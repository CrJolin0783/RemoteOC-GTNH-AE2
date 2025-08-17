from datetime import datetime
import json
import threading
import uuid
import copy
import os
from fastapi import HTTPException
from .utils import logger, READY, PENDING, COMPLETED
from .task import TaskManager, task_manager
from config import trigger_config


class TriggerManager:
    def __init__(self, task_manager: TaskManager):
        self.triggers = {}
        self.task_manager = task_manager  # 引入任务管理器
    
    def get_config_list(self) -> list:
        """
        获取触发器配置列表。
        """
        config_list = []
        for timer_name, trigger in trigger_config.items():
            config = {
                "name": timer_name,
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
        
    def get_tasks(self) -> dict:
        """
        获取所有任务。
        """
        tasks = {}
        for trigger_task_id, trigger in self.triggers.items():
            task_id = trigger.get("task", {}).get("task_id")
            if task_id:
                tasks[task_id] = trigger.get("task", {})
        return tasks

    def replace_placeholders(self, obj, params):
        """
        遍历字典或列表中的每个元素，替换占位符为对应的参数值。
        """
        if isinstance(obj, dict):
            # 如果是字典，递归替换每个键的值
            for key, value in obj.items():
                obj[key] = self.replace_placeholders(value, params)
        elif isinstance(obj, list):
            # 如果是列表，递归替换每个元素
            for i in range(len(obj)):
                obj[i] = self.replace_placeholders(obj[i], params)
        elif isinstance(obj, str):
            # 如果是字符串，使用 .format 替换占位符
            return obj.format(**params)
        return obj
    
    def replace_placeholders_2(self, data, params: dict):
        """
        递归替换字典中的占位符<XXX>为参数值。

        :param data: 要处理的数据，可以是嵌套的字典、列表或字符串。
        :param params: 参数字典。
        
        :return: 替换后的数据。
        """
        if isinstance(data, dict):
            return {key: self.replace_placeholders_2(value, params) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.replace_placeholders_2(item, params) for item in data]
        elif isinstance(data, str):
            for key, value in params.items():
                if not isinstance(value, str):
                    continue
                placeholder = f"<{key.upper()}>"
                if placeholder in data:
                    data = data.replace(placeholder, value)
            return data
        else:
            return data

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
        
        # 动态调用函数
        return func(**call_kwargs)

    def register_trigger(self, trigger_name, action_name, trigger_kwargs: dict, action_kwargs: dict, interval: int = None):
        """
        注册触发器。
        :param trigger_name: 触发器名称。
        :param action: 触发操作。
        :param trigger_args: 触发器参数。
        :param action_args: 操作参数。
        """
        if trigger_name not in trigger_config:
            logger.error(f"Trigger '{trigger_name}' not found.")
            raise HTTPException(status_code=404, detail=f"Trigger '{trigger_name}' not found.")
        config = copy.deepcopy(trigger_config[trigger_name])
        if action_name not in config.get('actions', {}):
            logger.error(f"Action '{action_name}' not found.")
            raise HTTPException(status_code=404, detail=f"Action '{action_name}' not found.")
        
        # 触发器名称
        config['name'] = trigger_name
        
        # 检测时间
        if interval is not None:
            config['interval'] = interval

        # 操作
        config['action'] = config['actions'][action_name]
        del config['actions']

        # 替换task占位符
        task_config = copy.deepcopy(config['task'])
        task_config = self.replace_placeholders(task_config, trigger_kwargs)
        config['task'] = task_config

        # 将触发器参数传入
        config['kwargs'] = copy.deepcopy(trigger_kwargs)

        # 将操作参数传入
        config['action']['action_kwargs'] = copy.deepcopy(action_kwargs)

        # 生命周期
        config['time'] = {
            "created": datetime.now().isoformat(),
            "last_start": None,
            "last_monitor": None,
            "completed": None,
        }

        # 其他属性
        config['result'] = None
        config['status'] = READY
        trigger_task_id = str(uuid.uuid4())
        config['running'] = False
        config['timer'] = None
        self.triggers[trigger_task_id] = config
        logger.debug(f"Trigger '{trigger_task_id}' registered.")
        return trigger_task_id

    def unregister_trigger(self, trigger_task_id):
        """
        注销触发器。
        :param trigger_task_id: 触发器ID。
        """
        if trigger_task_id in self.triggers:
            self.stop(trigger_task_id, force=True)
            del self.triggers[trigger_task_id]
        
    def _execute_task(self, task_config):
        """
        执行任务。
        :param task_config: 任务配置。
        """
        try:
            task_id = task_config['task_id']
            client_id = task_config['client_id']
            commands = task_config['commands']
            self.task_manager.add_task(task_id, client_id, commands, READY)
            logger.debug("Task added to task manager.")

        except Exception as e:
            logger.error(f"Error executing task: {e}")

    def _monitor_trigger(self, trigger_task_id):
        """
        监控触发器，执行任务。
        :param trigger_task_id: 触发器ID。
        :param config: 触发器配置。
        """
        try:
            config = self.triggers[trigger_task_id]

            if not config['running']:
                return
            
            logger.debug(f"Monitoring trigger '{trigger_task_id}'.")
            config['time']['last_monitor'] = datetime.now().isoformat()

            # 检查任务状态
            task_id = config.get('task', {}).get('task_id')
            if not task_id:
                task_id = str(uuid.uuid4())
                config['task']['task_id'] = task_id
            task_status = task_manager.get_task(task_id)

            if task_status:
                # 检查触发条件是否满足
                if task_status.get("status") == COMPLETED and task_status.get("results") == True:
                    # 执行操作
                    action = config['action']
                    trigger_kwargs = config.get('kwargs', {})
                    action_kwargs = action.get("action_kwargs", {})
                    # 替换action_kwargs中的占位符
                    action_kwargs = self.replace_placeholders_2(action_kwargs, trigger_kwargs)
                    action_kwargs = self.replace_placeholders_2(action_kwargs, os.environ)
                    config['result'] = {"success": True, "data": self.execute_action(action, action_kwargs)}
                    config['status'] = COMPLETED
                    config['time']['completed'] = datetime.now().isoformat()
                    self.stop(trigger_task_id, is_completed=True)
                    logger.debug(f"Action '{action['name']}' executed successfully.")

                elif task_status.get("status") == COMPLETED and task_status.get("results") != True:
                    self._execute_task(config['task'])
                    logger.debug(f"Task '{config['task']['task_id']}' executed.")
                else:
                    logger.debug(f"Task '{config['task']['task_id']}' is pending.")
            else:
                self._execute_task(config['task'])
                logger.debug(f"Task '{config['task']['task_id']}' executed.")
            
            # 重新启动定时器
            timer = threading.Timer(config.get("interval", 180), self._monitor_trigger, args=(trigger_task_id,))
            timer.start()
            config['timer'] = timer

        except Exception as e:
            logger.error(f"Error monitoring trigger '{trigger_task_id}': {e}")
            config['result'] = {"success": False, "error": str(e)}
            self.stop(trigger_task_id)

    def start(self, trigger_task_id):
        """
        启动触发器。
        :param trigger_task_id: 触发器ID。
        """
        if trigger_task_id not in self.triggers:
            logger.error(f"Trigger '{trigger_task_id}' not found.")
            raise HTTPException(status_code=404, detail=f"Trigger '{trigger_task_id}' not found.")

        trigger_config = self.triggers[trigger_task_id]
        if trigger_config['running']:
            logger.error(f"Trigger '{trigger_task_id}' is already running.")
            raise HTTPException(status_code=400, detail=f"Trigger '{trigger_task_id}' is already running.")

        trigger_config['running'] = True
        timer = threading.Timer(trigger_config.get("interval", 180), self._monitor_trigger, args=(trigger_task_id,))
        timer.start()
        trigger_config['timer'] = timer
        trigger_config['status'] = PENDING
        trigger_config['time']['last_start'] = datetime.now().isoformat()
        logger.debug(f"Trigger '{trigger_task_id}' started.")

    def stop(self, trigger_task_id, force=False, is_completed=False):
        """
        停止触发器。
        :param trigger_task_id: 触发器ID。
        :param force: 是否强制停止。
        """
        if trigger_task_id not in self.triggers:
            logger.error(f"Trigger '{trigger_task_id}' not found.")
            raise HTTPException(status_code=404, detail=f"Trigger '{trigger_task_id}' not found.")

        trigger_config = self.triggers[trigger_task_id]
        if not trigger_config['running'] and not force:
            logger.error(f"Trigger '{trigger_task_id}' is not running.")
            raise HTTPException(status_code=400, detail=f"Trigger '{trigger_task_id}' is not running.")

        trigger_config['running'] = False
        timer = trigger_config.get('timer')
        if timer:
            timer.cancel()
            trigger_config['timer'] = None
            trigger_config['status'] = COMPLETED if is_completed else READY
            task_manager.remove_task(trigger_config.get('task', {}).get('task_id'))
            logger.debug(f"Trigger '{trigger_task_id}' stopped.")
    
    def get_trigger_list(self):
        """
        获取所有触发器。
        """
        return self.triggers
    
    def stop_all(self):
        """
        停止所有触发器。
        """
        for trigger_task_id in self.triggers:
            if self.triggers[trigger_task_id]['running']:
                self.stop(trigger_task_id)
        logger.debug("All triggers stopped.")


trigger_manager = TriggerManager(task_manager)
