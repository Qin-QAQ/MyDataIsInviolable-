#!/usr/bin/env python3

# 导入自定义模块
from infocollector import get_disk_info
from speed_tester import get_disk_mount_map, test_write_speed, test_read_speed, SYSTEM_DISK
from capacity_check import f3_write, f3_read, cleanup_f3_files
# !/usr/bin/env python3
import sys
import os
import signal

# 全局标志
running = True


def signal_handler(sig, frame):
    """处理 Ctrl+C 信号"""
    global running
    print("\n\n⚠️  收到中断信号，正在退出...")
    running = False
    sys.exit(0)


# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)


# ... 导入模块 ...

def safe_input(prompt=""):
    """安全的 input，可被中断"""
    try:
        return input(prompt)
    except KeyboardInterrupt:
        print("\n⚠️  操作取消")
        return None


def main():
    global running

    if os.geteuid() != 0:
        print("⚠️  警告：建议使用 sudo 运行以获得完整功能")
        print()

    while running:
        print_header()
        print("1. 查看硬盘信息 (SMART)")
        print("2. 测试读写速度")
        print("3. 检测真实容量 (打假)")
        print("0. 退出")
        print()

        choice = safe_input("请选择功能：")
        if choice is None:
            continue

        if choice == '1':
            print("\n--- 硬盘信息 ---")
            mount_map = get_disk_mount_map()
            if not mount_map:
                return

            devs = list(mount_map.keys())
            print("可用磁盘：")
            for i, dev in enumerate(devs, 1):
                mount = mount_map[dev]
                status = f"→ {mount}" if mount else "(未挂载)"
                mark = "⚠️  系统盘" if dev == SYSTEM_DISK else ""
                print(f"  {i}. {dev} {status} {mark}")

            try:
                choice = int(input("\n选择磁盘编号："))
                device = devs[choice - 1]

            except (ValueError, IndexError):
                print("❌ 无效选择")
                return
            if device:
                menu_info(device)
        elif choice == '2':
            menu_speed()
        elif choice == '3':
            menu_capacity()
        elif choice == '0':
            print("\n👋 再见！数据安全第一！")
            break
        else:
            print("❌ 无效选项")

        if running:
            safe_input("\n按回车键继续...")


def menu_info(device):
    """修改为接收设备参数"""
    info = get_disk_info(device)
    print("\n📊 检测结果：")
    for k, v in info.items():
        print(f"  {k}: {v}")
    print()


# ... 其余代码 ...




def print_header():
    print("=" * 60)
    print("=== 硬盘检测器 (MyDataIsInviolable!) ===")
    print("=" * 60)
    print()


def menu_speed():
    """菜单 2: 测速"""
    print("\n--- 硬盘测速 ---")
    mount_map = get_disk_mount_map()
    if not mount_map:
        return

    devs = list(mount_map.keys())
    print("可用磁盘：")
    for i, dev in enumerate(devs, 1):
        mount = mount_map[dev]
        status = f"→ {mount}" if mount else "(未挂载)"
        mark = "⚠️  系统盘" if dev == SYSTEM_DISK else ""
        print(f"  {i}. {dev} {status} {mark}")

    try:
        choice = int(input("\n选择磁盘编号："))
        selected_dev = devs[choice - 1]
        selected_mount = mount_map[selected_dev]
    except (ValueError, IndexError):
        print("❌ 无效选择")
        return

    print(f"\n✅ 已选择：{selected_dev}")

    # 写入
    if selected_mount and selected_dev != SYSTEM_DISK:
        res = test_write_speed(selected_mount)
        if res.get("write_speed_mb_s"):
            print(f"📝 写入：{res['write_speed_mb_s']} MB/s")
        else:
            print(f"❌ 写入失败：{res.get('error')}")
    else:
        print("⏭️  跳过写入")

    # 读取
    if selected_dev != SYSTEM_DISK:
        res = test_read_speed(selected_dev)
        if res.get("read_speed_mb_s"):
            print(f"📖 读取：{res['read_speed_mb_s']} MB/s")
        else:
            print(f"❌ 读取失败：{res.get('error')}")
    else:
        print("⏭️  跳过读取")


def menu_capacity():
    """菜单 3: 容量检测"""
    print("\n--- 容量检测 (F3 打假) ---")
    print("⚠️  警告：此操作会写满磁盘空间！")

    mount_map = get_disk_mount_map()
    devs = list(mount_map.keys())

    print("可用磁盘：")
    for i, dev in enumerate(devs, 1):
        mount = mount_map[dev]
        status = f"→ {mount}" if mount else "(未挂载)"
        mark = "⚠️  系统盘" if dev == SYSTEM_DISK else ""
        print(f"  {i}. {dev} {status} {mark}")

    try:
        choice = int(input("\n选择磁盘编号："))
        selected_dev = devs[choice - 1]
        selected_mount = mount_map[selected_dev]
    except (ValueError, IndexError):
        print("❌ 无效选择")
        return

    if selected_dev == SYSTEM_DISK or not selected_mount:
        print("❌ 无法测试（系统盘或未挂载）")
        return

    # 执行 F3
    if f3_write(selected_mount):
        f3_read(selected_mount)
        cleanup = input("\n是否清理测试文件？(y/n): ")
        if cleanup.lower() == 'y':
            cleanup_f3_files(selected_mount)




if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  程序中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        sys.exit(1)