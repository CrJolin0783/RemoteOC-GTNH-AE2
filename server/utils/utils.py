import logging
import os
from dotenv import load_dotenv


if os.path.exists(".env.dev"):
    load_dotenv(".env.dev")

load_dotenv()

levels = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}
LOG_LEVEL = levels.get(os.getenv("LOG_LEVEL"), "INFO")

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("uvicorn.error")

# 任务状态常量
READY = "ready"
PENDING = "pending"
UPLOADING = "uploading"
COMPLETED = "completed"


def decode_request_body(body: bytes) -> str:
    """
    尝试使用 utf-8 和 gbk 解码请求体
    :param body: 请求体的原始字节数据
    :return: 解码后的字符串
    :raises UnicodeDecodeError: 如果所有解码都失败
    """
    # 尝试使用 utf-8 解码
    try:
        decoded_body = body.decode("utf-8")
        return decoded_body
    except UnicodeDecodeError:
        # 如果 utf-8 解析失败，尝试使用 gbk 解析
        try:
            decoded_body = body.decode("gbk")
            logger.debug("utf-8 解析失败，使用 gbk 解析请求体")
            return decoded_body
        except UnicodeDecodeError as e:
            logger.error(f"utf-8 和 gbk 解析均失败: {str(e)}")
            raise UnicodeDecodeError("无法解析请求体为 utf-8 或 gbk")

