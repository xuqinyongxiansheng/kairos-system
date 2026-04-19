"""Kairos System 入口点，支持 python -m kairos 启动"""
import sys
import os

def main():
    src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    from kairos.main import app
    import uvicorn
    host = os.environ.get("GEMMA4_HOST", "0.0.0.0")
    port = int(os.environ.get("GEMMA4_PORT", "8080"))
    print("=" * 60)
    print("  Kairos System v4.1.0")
    print("  智能集成系统核心")
    print("=" * 60)
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()
