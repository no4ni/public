import sys
print("Python путь:", sys.executable)

missing_modules = []
required_modules = [
    "langchain_core",
    "langchain",
    "llama_cpp",
    "ddgs",
    "requests",
    "colorama"
]

for module in required_modules:
    try:
        __import__(module)
        print(f"✓ {module} доступен")
    except ImportError:
        print(f"✗ {module} отсутствует")
        missing_modules.append(module)

if missing_modules:
    print(f"\nОтсутствуют модули: {missing_modules}")
else:
    print("\nВсе необходимые модули установлены!")
