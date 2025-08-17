import uuid
import requests
from utils.utils import READY
from utils.task import task_manager


def craft_item(client_id, item_name, item_damage, item_amount=1, cpu_name=None, label=None):
    """
    请求合成物品
    :param item_name: 物品名称
    :param item_damage: 物品伤害值
    :param item_amount: 物品数量
    :param cpu_name: CPU 名称
    :param label: 标签
    """

    if cpu_name:
        command = f"return ae.requestItem('{item_name}', {item_damage}, {item_amount}, '{cpu_name}', '{label}')" if label else f"return ae.requestItem('{item_name}', {item_damage}, {item_amount}, '{cpu_name}')"
    else:
        command = f"return ae.requestItem('{item_name}', {item_damage}, {item_amount}, nil, '{label}')" if label else f"return ae.requestItem('{item_name}', {item_damage}, {item_amount})"
    
    task_id = str(uuid.uuid4())

    task_manager.add_task(
        task_id=task_id,
        client_id=client_id,
        commands=[
            command
        ],
        status=READY,
        is_chunked=False
    )
    return task_id


def send_notification(method: str, url: str, headers=None, params=None, data=None):
    """
    发送通知

    通过请求url发送通知
    :param method: 请求方法
    :param url: 请求地址
    :param headers: 请求头
    :param params: 请求参数
    :param data: 请求数据
    """
    if not params:
        params = {}
    if not data:
        data = {}
    if not headers:
        headers = {}
    try:
        res = requests.request(method, url, headers=headers, params=params, json=data, timeout=5)
        return res.text
    except Exception as e:
        return str(e)
    