#!/usr/bin/env python3
import subprocess
import os
import time
import json

SYSTEM_DISK = "/dev/sda"


def get_disk_mount_map():
    """自动获取设备名和挂载点的映射"""
    try:
        result = subprocess.run(
            ['lsblk', '-J', '-o', 'NAME,MOUNTPOINT,TYPE,SIZE'],
            capture_output=True,
            text=True
        )
        data = json.loads(result.stdout)

        mount_map = {}
        for block in data.get('blockdevices', []):
            if block.get('type') == 'disk':
                device_name = f"/dev/{block.get('name')}"
                mount_point = None
                for partition in block.get('children', []):
                    if partition.get('mountpoint'):
                        mount_point = partition.get('mountpoint')
                        break
                mount_map[device_name] = mount_point
        return mount_map
    except Exception as e:
        print(f"❌ 获取磁盘列表失败：{e}")
        return {}


def test_write_speed(mount_point, file_size_mb=512):
    """测试写入速度"""
    if not mount_point or not os.path.exists(mount_point):
        return {"error": "挂载点不存在"}

    file_name = os.path.join(mount_point, ".speed_test_temp_file.bin")

    try:
        print(f"🔄 正在写入 {file_size_mb}MB 测试数据...")
        cmd = f"dd if=/dev/zero of={file_name} bs=1M count={file_size_mb} oflag=direct"

        start_time = time.time()
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        end_time = time.time()

        if os.path.exists(file_name):
            os.remove(file_name)

        if result.returncode == 0:
            duration = end_time - start_time
            speed = file_size_mb / duration if duration > 0 else 0
            return {"write_speed_mb_s": round(speed, 2)}
        else:
            return {"error": result.stderr}
    except Exception as e:
        return {"error": str(e)}


def test_read_speed(device_path, size_mb=512):
    """测试读取速度"""
    if device_path == SYSTEM_DISK:
        return {"error": "⚠️  禁止对系统盘进行读取测试"}

    try:
        print(f"🔄 正在从 {device_path} 读取 {size_mb}MB 数据...")
        cmd = f"sudo dd if={device_path} of=/dev/null bs=1M count={size_mb} iflag=direct"

        start_time = time.time()
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        end_time = time.time()

        if result.returncode == 0:
            duration = end_time - start_time
            speed = size_mb / duration if duration > 0 else 0
            return {"read_speed_mb_s": round(speed, 2)}
        else:
            return {"error": result.stderr}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    print("=== 硬盘测速工具 (自动识别版) ===\n")

    mount_map = get_disk_mount_map()

    if not mount_map:
        exit(1)

    print("发现以下磁盘：")
    devs = list(mount_map.keys())
    for i, dev in enumerate(devs, 1):
        mount = mount_map[dev]
        status = f"→ {mount}" if mount else "(未挂载)"
        mark = "⚠️  系统盘" if dev == SYSTEM_DISK else ""
        print(f"  {i}. {dev} {status} {mark}")
    print()

    try:
        choice = int(input("请选择磁盘编号："))
        selected_dev = devs[choice - 1]
        selected_mount = mount_map[selected_dev]
    except (ValueError, IndexError):
        print("❌ 无效选择")
        exit(1)

    print(f"\n✅ 已选择：{selected_dev}")
    if selected_mount:
        print(f"📁 挂载点：{selected_mount}")
    else:
        print("⚠️  未挂载，跳过写入测试")
    print()

    # 写入测试
    if selected_mount and selected_dev != SYSTEM_DISK:
        write_result = test_write_speed(selected_mount)
        if write_result.get("write_speed_mb_s"):
            print(f"📝 写入速度：{write_result['write_speed_mb_s']} MB/s")
        else:
            print(f"❌ 写入失败：{write_result.get('error')}")
    elif selected_dev == SYSTEM_DISK:
        print("⏭️  跳过写入测试（系统盘保护）")
    else:
        print("⏭️  跳过写入测试（无挂载点）")

    # 读取测试
    if selected_dev != SYSTEM_DISK:
        read_result = test_read_speed(selected_dev)
        if read_result.get("read_speed_mb_s"):
            print(f"📖 读取速度：{read_result['read_speed_mb_s']} MB/s")
        else:
            print(f"❌ 读取失败：{read_result.get('error')}")
    else:
        print("⏭️  跳过读取测试（系统盘保护）")