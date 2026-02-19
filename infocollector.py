import subprocess
import json
import os

def is_root():
    """检查是否以 root 权限运行"""
    return os.geteuid() == 0
def get_disk_info(device_path):
    """
    获取硬盘详细信息
    device_path 例如：/dev/sda
    """
    try:
        cmd_prefix = ['sudo'] if not is_root() else []

        result = subprocess.run(
            cmd_prefix + ['smartctl', '--json', '-i', '-A', device_path],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return {"error": "无法读取信息，可能需要 sudo 权限或设备不存在", "stderr": result.stderr}

        data = json.loads(result.stdout)

        # 1. 获取容量 (GB)
        capacity_bytes = data.get("user_capacity", {}).get("bytes", 0)
        capacity_gb = round(capacity_bytes / (1024 ** 3), 2)

        # 2. 判断硬盘类型
        rotation = data.get("rotation_rate", 0)
        if rotation > 0:
            disk_type = f"HDD ({rotation} RPM)"
        elif rotation == 0:
            disk_type = "SSD"
        else:
            disk_type = "Unknown"
        # 3. 提取关键信息
        _info = {
            "设备": device_path,
            "磁盘型号": data.get("model_name", "Unknown"),
            "设备序列号": data.get("serial_number", "Unknown"),
            "总空间": capacity_bytes,
            "总存储空间（GB）": capacity_gb,
            "磁盘类型": disk_type,
            "理论速度": data.get("interface_speed", {}).get("current", {}).get("string", "Unknown"),
            "支持智能？": data.get("smart_support", {}).get("enabled", "Unknown"),
        }

        # 4. 解析 SMART 属性 (通电时间、温度等)
        # 注意：不同硬盘的属性 ID 可能不同，以下是常见值
        for attr in data.get("ata_smart_attributes", {}).get("table", []):
            attr_name = attr.get("name", "")
            raw_value = attr.get("raw", {}).get("value", 0)

            if attr_name == "Power_On_Hours":
                _info["通电天数"] = raw_value
            elif attr_name in ["Temperature_Celsius", "Temperature"]:
                _info["磁盘温度"] = raw_value

        return _info

    except json.JSONDecodeError as e:
        return {"error": f"JSON 解析失败：{str(e)}"}
    except Exception as e:
        return {"error": f"未知错误：{str(e)}"}


# 测试
if __name__ == "__main__":
    device = input("输入设备路径 (如 /dev/sda): ")
    info = get_disk_info(device)
    print("\n=== 硬盘信息 ===")
    for k, v in info.items():
        print(f"{k}: {v}")