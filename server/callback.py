import json
import time

monitor_data = {
    "last": None,
    "current": None,
}


def test(result: list):
    print(result)


def parse_data(result: list):
    capacitor_info = json.loads(result[0])
    fluid = json.loads(result[1])
    item = json.loads(result[2])
    data = [capacitor_info, fluid, item]
    if monitor_data.get("current") is not None:
        monitor_data["last"] = monitor_data.get("current")
    monitor_data["current"] = data
    return monitor_data


def check_cpu_free(result: list):
    cpu_status = json.loads(result[0]).get("data", {})
    return cpu_status.get("busy") == False


def auto_upload_data_callback(results):
    """自动上传数据回调函数"""
    # 将数据存储到分布式缓存中
    try:
        from utils.cache import distributed_cache
        
        # 根据任务类型确定缓存键
        if "getCpuList" in str(results):
            cache_key = "ae_cpu_data"
            data_type = "cpu"
        elif "getAllSilempleItems" in str(results):
            cache_key = "ae_item_data"
            data_type = "item"
        else:
            cache_key = "ae_unknown_data"
            data_type = "unknown"
        
        # 存储数据到缓存
        cached_result = distributed_cache.set(cache_key, {
            "data": results,
            "type": data_type,
            "timestamp": time.time(),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }, ttl=300)  # 缓存5分钟
        
        print(f"Auto uploaded {data_type} data to cache with key: {cache_key}, result: {cached_result}")
        return results
    except Exception as e:
        print(f"Error in auto_upload_data_callback: {e}")
        return results
    