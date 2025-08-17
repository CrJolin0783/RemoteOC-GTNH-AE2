import json
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from datetime import datetime, timedelta
from fastapi import HTTPException
from typing import Callable, List, Optional
from config import timer_config
from utils.utils import logger, READY, PENDING, COMPLETED
import copy
import uuid


class TimerManager:
    def __init__(self):
        # 初始化定时器管理器
        self.scheduler = BackgroundScheduler(jobstores={'default': MemoryJobStore()})
        self.scheduler.start()
        self.timer = {}

    def get_config_list(self) -> list:
        """
        获取触发器配置列表。
        """
        config_list = []
        for trigger_name, trigger in timer_config.items():
            config = {
                "name": trigger_name,
                "description": trigger.get("description"),
                "args": trigger.get("args", []),
                "actions": []
            }
            for action_id, action in trigger.get("actions", {}).items():
                config["actions"].append({
                    "id": action_id,
                    "name": action.get("name"),
                    "description": action.get("description"),
                    "args": action.get("args", []),
                })
            config_list.append(config)
        return config_list

    def execute_action(self, action, action_kwargs):
        """
        根据 action 的定义，动态调用对应的函数。
        :param action: 定义了函数信息和参数的字典
        :param action_kwargs: 传入的参数字典
        """
        # 提取函数
        func = action.get("function")
        if not callable(func):
            raise ValueError("指定的 function 不是可调用对象")
        
        # 提取参数定义
        args_def = action.get("args", [])
        
        # 构造函数调用所需的参数
        call_kwargs = {}
        for arg in args_def:
            field_name = arg["field"]
            field_type = arg.get("type")
            default_value = arg.get("default", None)
            
            # 获取值，如果未提供则使用默认值
            value = action_kwargs.get(field_name, default_value)

            # 类型转换
            if isinstance(value, str):
                if field_type == "int":
                    value = int(value)
                elif field_type == "float":
                    value = float(value)
                elif field_type == "bool":
                    value = value.lower() == "true"
                elif field_type == "dict":
                    value = json.loads(value)
                elif field_type == "list":
                    value = json.loads(value)
                elif field_type == "str":
                    value = str(value)
            
            call_kwargs[field_name] = value
        
        logger.debug(f"Executing action '{action['name']}'")
        # 动态调用函数
        return func(**call_kwargs)
    
    def _excute_timer(self, timer_id: str):
        """
        执行定时任务
        :param timer_id: 任务ID
        """
        timer_config = self.timer[timer_id]
        try:
            action = timer_config['action']
            action_kwargs = timer_config['action']['action_kwargs']
            result = self.execute_action(action, action_kwargs)
            timer_config['result'] = result
        except Exception as e:
            logger.error(f"Error occurred while executing timer '{timer_id}': {str(e)}")
        finally:
            timer_config['status'] = COMPLETED
            timer_config['time']['completed'] = datetime.now().isoformat()
            timer_config['running'] = False

    def register_timer(self, timer_name, action_name, timer_kwargs: dict, action_kwargs: dict):
        """
        注册一个新的定时任务
        :param timer_name: 触发器名称
        :param action_name: 操作名称
        :param timer_kwargs: 触发器参数
        :param action_kwargs: 操作参数
        """
        if timer_name == "延迟任务":
            current_time = datetime.now()
            run_date = current_time + timedelta(seconds=timer_kwargs["delay"])
        elif timer_name == "定时任务":
            run_date = datetime.fromisoformat(timer_kwargs["time"])
        else:
            raise HTTPException(status_code=400, detail="不支持的触发类型")
        
        config = copy.deepcopy(timer_config[timer_name])
        if action_name not in config.get('actions', {}):
            logger.error(f"Action '{action_name}' not found.")
            raise HTTPException(status_code=404, detail=f"Action '{action_name}' not found.")
        
        # 名称
        config['name'] = timer_name

        # 操作
        config['action'] = config['actions'][action_name]
        del config['actions']

        # 将触发器参数传入
        config['kwargs'] = copy.deepcopy(timer_kwargs)

        # 将操作参数传入
        config['action']['action_kwargs'] = copy.deepcopy(action_kwargs)

        # 生命周期
        config['time'] = {
            "created": datetime.now().isoformat(),
            "last_start": None,
            "excuted": run_date.isoformat(),
            "completed": None,
        }

        # 其他属性
        config['result'] = None
        config['status'] = READY
        timer_id = str(uuid.uuid4())
        config['running'] = False

        self.timer[timer_id] = config
        
        # 添加定时任务
        job = self.scheduler.add_job(
            self._excute_timer, 
            DateTrigger(run_date=run_date), 
            args=[timer_id],
            id=timer_id
        )
        job.pause()

        logger.debug(f"Timer '{timer_id}' registered.")
        return timer_id

    def unregister_timer(self, timer_id: str):
        """
        注销指定的定时任务
        :param timer_id: 任务ID
        """
        if timer_id not in self.timer:
            logger.error(f"Timer '{timer_id}' not found.")
            raise HTTPException(status_code=404, detail=f"Timer '{timer_id}' not found.")
        del self.timer[timer_id]
        job = self.scheduler.get_job(timer_id)
        if job:
            self.scheduler.remove_job(timer_id)

    def start(self, timer_id: str):
        """
        启动指定的定时任务
        :param timer_id: 任务ID
        """
        if timer_id not in self.timer:
            logger.error(f"Timer '{timer_id}' not found.")
            raise HTTPException(status_code=404, detail=f"Timer '{timer_id}' not found.")

        timer_config = self.timer[timer_id]
        if timer_config['running']:
            logger.error(f"Timer '{timer_id}' is already running.")
            raise HTTPException(status_code=400, detail=f"Timer '{timer_id}' is already running.")
        
        # 判断当前时间是否已经超过了任务的执行时间
        run_date = datetime.fromisoformat(timer_config['time']['excuted'])
        if run_date < datetime.now():
            logger.error(f"Timer '{timer_id}' is already expired.")
            raise HTTPException(status_code=400, detail=f"Timer '{timer_id}' is already expired.")
        
        job = self.scheduler.get_job(timer_id)
        if job:
            job.resume()
            timer_config['running'] = True
            timer_config['status'] = PENDING
            timer_config['time']['last_start'] = datetime.now().isoformat()
        else:
            logger.error(f"Timer '{timer_id}' not found.")
            raise HTTPException(status_code=404, detail=f"Timer '{timer_id}' not found.")

    def stop(self, timer_id: str, force=False):
        """
        停止指定的定时任务
        :param timer_id: 任务ID
        :param force: 是否强制停止
        """
        if timer_id not in self.timer:
            logger.error(f"Timer '{timer_id}' not found.")
            raise HTTPException(status_code=404, detail=f"Timer '{timer_id}' not found.")
        
        timer_config = self.timer[timer_id]
        if not timer_config['running'] and not force:
            logger.error(f"Timer '{timer_id}' is not running.")
            raise HTTPException(status_code=400, detail=f"Timer '{timer_id}' is not running.")
        
        job = self.scheduler.get_job(timer_id)
        if job:
            job.pause()
            timer_config['running'] = False
            timer_config['status'] = READY
        else:
            logger.error(f"Timer '{timer_id}' not found.")
            raise HTTPException(status_code=404, detail=f"Timer '{timer_id}' not found.")

    def get_timer_list(self) -> List[dict]:
        """
        获取所有已注册的定时任务
        """
        return self.timer

    def stop_all(self):
        """
        停止所有定时任务
        """
        for timer_id in self.timer:
            if self.timer[timer_id]['running']:
                self.stop_timer(timer_id, force=True)
        logger.info("All timers stopped.")


timer_manager = TimerManager()
