#!/usr/bin/env python3
import subprocess
import os
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

        _mount_map = {}
        for block in data.get('blockdevices', []):
            if block.get('type') == 'disk':
                device_name = f"/dev/{block.get('name')}"
                mount_point = None
                for partition in block.get('children', []):
                    if partition.get('mountpoint'):
                        mount_point = partition.get('mountpoint')
                        break
                _mount_map[device_name] = mount_point
        return _mount_map
    except Exception as e:
        print(f"❌ 获取磁盘列表失败：{e}")
        return {}


def check_free_space(mount_point):
    """检查挂载点剩余空间"""
    try:
        result = subprocess.run(
            ['df', '-B1', mount_point],
            capture_output=True,
            text=True
        )
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            available_bytes = int(parts[3])
            return available_bytes
    except Exception as e:
        print(f"❌ 获取磁盘列表失败：{e}")
        pass
    return 0


def f3_write(mount_point):
    """
    执行 f3write，写满整个可用空间
    ⚠️  这会占用所有剩余空间！
    """
    print(f"\n⚠️  警告：f3write 将写满 {mount_point} 的所有可用空间！")
    print("   这会删除该分区上已有的文件吗？不会，但会占满空间导致无法写入新文件。")
    print()

    free_space = check_free_space(mount_point)
    free_gb = round(free_space / (1024 ** 3), 2)
    print(f"📊 当前可用空间：{free_gb} GB")
    print()

    confirm = input("⚠️  确认继续？(输入 YES 继续): ")
    if confirm != "YES":
        print("❌ 用户取消")
        return None

    try:
        print("\n🔄 开始写入测试数据（这可能需要很长时间）...")
        print("   进度会实时显示，请耐心等待...\n")

        result = subprocess.run(
            ['f3write', mount_point],
            capture_output=False,  # 直接输出到终端，可以看到进度
            text=True
        )

        if result.returncode == 0:
            print("\n✅ f3write 完成！")
            return True
        else:
            print(f"\n❌ f3write 失败：{result.stderr}")
            return False
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        return None
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        return False


def f3_read(mount_point):
    """
    执行 f3read，验证写入的数据
    """
    print("\n🔄 开始验证数据完整性...")
    print("   这需要读取刚才写入的所有数据...\n")

    try:
        result = subprocess.run(
            ['f3read', mount_point],
            capture_output=True,
            text=True
        )

        # 输出完整结果
        print(result.stdout)
        if result.stderr:
            print(result.stderr)

        # 解析结果
        output = result.stdout
        is_fake = False

        if "Data lost" in output or "data lost" in output:
            is_fake = True
            print("\n❌ 检测到数据丢失！这很可能是扩容盘！")
        elif "OK" in output and result.returncode == 0:
            print("\n✅ 数据验证通过，容量真实！")
        else:
            print("\n⚠️  无法确定结果，请查看上方输出")

        return {"is_fake": is_fake, "output": output}
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        return None
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        return None


def cleanup_f3_files(mount_point):
    """清理 f3 生成的测试文件"""
    print("\n🧹 清理测试文件...")
    try:
        for filename in os.listdir(mount_point):
            if filename.startswith('.f3'):
                filepath = os.path.join(mount_point, filename)
                os.remove(filepath)
                print(f"  已删除：{filename}")
        print("✅ 清理完成")
    except Exception as e:
        print(f"❌ 清理失败：{e}")


if __name__ == "__main__":
    import json

    print("=" * 50)
    print("=== 硬盘容量检测工具 (F3 打假版) ===")
    print("=" * 50)
    print()
    print("⚠️  重要提示：")
    print("   1. 此测试会写满整个磁盘空间")
    print("   2. 测试完成后需要手动清理测试文件")
    print("   3. 仅对 U 盘/移动硬盘使用，禁止对系统盘使用")
    print()

    mount_map = get_disk_mount_map()
    if not mount_map:
        exit(1)

    print("可用磁盘：")
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

    if selected_dev == SYSTEM_DISK:
        print("\n❌ 禁止对系统盘进行容量检测！")
        exit(1)

    if not selected_mount:
        print("\n❌ 磁盘未挂载，无法测试")
        exit(1)

    print(f"\n✅ 已选择：{selected_dev}")
    print(f"📁 挂载点：{selected_mount}")

    # 执行 f3write
    write_result = f3_write(selected_mount)
    if not write_result:
        print("\n❌ 写入测试未完成的，无法继续验证")
        exit(1)

    # 执行 f3read
    read_result = f3_read(selected_mount)
    if read_result:
        if read_result.get("is_fake"):
            print("\n" + "=" * 50)
            print("🚨 结论：这很可能是一个扩容盘！")
            print("=" * 50)
        else:
            print("\n" + "=" * 50)
            print("✅ 结论：容量真实，可以放心使用")
            print("=" * 50)

    # 询问是否清理
    print()
    cleanup = input("是否清理测试文件？(推荐清理，输入 y 确认): ")
    if cleanup.lower() == 'y':
        cleanup_f3_files(selected_mount)
    else:
        print("\n⚠️  测试文件仍占用空间，请手动删除 .f3* 文件")