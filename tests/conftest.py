"""pytest 全局配置"""
import sys
from pathlib import Path

# 把 src/ 加入 import 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
