"""重置设置"""
import os
import json

os.chdir(os.path.dirname(os.path.dirname(__file__)))  # type: ignore

if input("确定要恢复初始状态吗？（y/n）") == "y":
    try:
        with open("datas/config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            config["first_run"] = True
            config["precision"] = 12
            config["precisionSet"] = 12
            config["precisionMode"] = 5
            config["showUnusual"] = False
        with open("datas/config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except:
        raise
    else:
        print("完成")
    finally:
        input("回车退出...")
