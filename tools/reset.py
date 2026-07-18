import json
if input("确定要恢复初始状态吗？（y/n）") == "y":
    try:
        with open("../datas/config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            config["first_run"] = True
        with open("../datas/config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False)
    except:
        raise
    else:
        print("完成")
    finally:
        input()
else:
    input("已取消")
