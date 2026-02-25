"""
生成 AegisVault 安装包
1. 先用 PyInstaller 打包 EXE
2. 再用 Inno Setup 生成安装程序
"""
import os, subprocess, sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("  密盾 AegisVault 安装包构建")
print("=" * 50)

print("\n[1/2] PyInstaller 打包...")
subprocess.run([sys.executable, "build_gui.py"], check=True)

print("\n[2/2] Inno Setup 生成安装包...")
os.makedirs("output", exist_ok=True)

iscc_paths = [
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
]
iscc = None
for p in iscc_paths:
    if os.path.exists(p): iscc = p; break

if iscc:
    subprocess.run([iscc, "installer.iss"], check=True)
    print("\n" + "=" * 50)
    print("  安装包已生成!")
    print("  output/AegisVault_Setup_v3.0.exe")
    print("  把这个文件发给别人即可安装使用")
    print("=" * 50)
else:
    print("错误: 找不到 Inno Setup")
    print("请安装 Inno Setup 6: https://jrsoftware.org/isdl.php")
