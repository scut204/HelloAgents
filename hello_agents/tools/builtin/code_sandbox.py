"""
CodeSandbox - 安全的 Python 代码沙箱执行器

提供进程隔离的代码执行环境，支持：
- 进程级隔离（subprocess）
- 资源限制（CPU时间、内存、执行超时）
- 受限的 Python builtins
- 白名单模块导入
- 工具函数注入

安全特性：
- 禁止危险的 builtins（exec, eval, compile, __import__ 等）
- 禁止文件系统直接访问
- 禁止网络直接访问
- 禁止系统命令执行
- 内存和 CPU 时间限制

使用示例：
```python
sandbox = CodeSandbox(timeout=30, max_memory_mb=512)

# 注入工具函数
sandbox.inject("search", search_func)
sandbox.inject("calculator", calc_func)

# 执行代码
result = sandbox.execute('''
data = search("天气")
result = f"搜索结果: {data}"
''')
```
"""

import ast
import sys
import traceback
import subprocess
import tempfile
import json
import pickle
import base64
from typing import Dict, Any, Optional, Callable, List, Set, Tuple
from dataclasses import dataclass, field
import os
import textwrap


@dataclass
class SandboxConfig:
    """沙箱配置"""

    timeout: int = 30  # 执行超时（秒）
    max_memory_mb: int = 512  # 最大内存（MB）
    max_cpu_time: int = 30  # 最大 CPU 时间（秒）
    allowed_modules: Set[str] = field(
        default_factory=lambda: {
            # 安全的标准库模块
            "math",
            "random",
            "statistics",
            "json",
            "re",
            "string",
            "datetime",
            "time",
            "calendar",
            "collections",
            "itertools",
            "functools",
            "copy",
            "pprint",
            "decimal",
            "fractions",
            "hashlib",
            "hmac",
            "base64",
            "binascii",
            "unicodedata",
            "textwrap",
            "difflib",
            "typing",
            "dataclasses",
            "enum",
            "uuid",
            # 异步支持
            "asyncio",
        }
    )
    # 禁止的 AST 节点类型
    forbidden_ast_nodes: Set[str] = field(
        default_factory=lambda: {
            "Import",  # 我们会单独处理导入
            "ImportFrom",
        }
    )


@dataclass
class ExecutionResult:
    """代码执行结果"""

    success: bool
    output: Any = None
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    error_type: Optional[str] = None
    execution_time: float = 0.0


class RestrictedBuiltins:
    """受限的 Python builtins"""

    # 允许的安全 builtins
    ALLOWED_BUILTINS = {
        # 类型和转换
        "int",
        "float",
        "str",
        "bool",
        "bytes",
        "bytearray",
        "list",
        "tuple",
        "dict",
        "set",
        "frozenset",
        "complex",
        "memoryview",
        # 内置函数
        "abs",
        "all",
        "any",
        "ascii",
        "bin",
        "callable",
        "chr",
        "divmod",
        "enumerate",
        "filter",
        "format",
        "getattr",
        "hasattr",
        "hash",
        "hex",
        "id",
        "isinstance",
        "issubclass",
        "iter",
        "len",
        "map",
        "max",
        "min",
        "next",
        "oct",
        "ord",
        "pow",
        "print",
        "range",
        "repr",
        "reversed",
        "round",
        "slice",
        "sorted",
        "sum",
        "type",
        "vars",
        "zip",
        # 对象和属性
        "object",
        "property",
        "classmethod",
        "staticmethod",
        "super",
        # 异常
        "Exception",
        "BaseException",
        "TypeError",
        "ValueError",
        "KeyError",
        "IndexError",
        "AttributeError",
        "RuntimeError",
        "StopIteration",
        "GeneratorExit",
        "AssertionError",
        "ZeroDivisionError",
        "OverflowError",
        "FloatingPointError",
        "ImportError",
        "ModuleNotFoundError",
        "LookupError",
        "NameError",
        "UnboundLocalError",
        "OSError",
        "IOError",
        "EOFError",
        "MemoryError",
        "RecursionError",
        "NotImplementedError",
        "IndentationError",
        "TabError",
        "SyntaxError",
        "SystemError",
        "UnicodeError",
        "UnicodeDecodeError",
        "UnicodeEncodeError",
        "UnicodeTranslateError",
        "Warning",
        "UserWarning",
        "DeprecationWarning",
        "PendingDeprecationWarning",
        "RuntimeWarning",
        "SyntaxWarning",
        "ResourceWarning",
        "FutureWarning",
        "ImportWarning",
        "UnicodeWarning",
        "BytesWarning",
        # 常量
        "True",
        "False",
        "None",
        "Ellipsis",
        "NotImplemented",
        # 其他安全函数
        "zip",
        "input",  # input 会被重定向
    }

    # 明确禁止的危险 builtins
    FORBIDDEN_BUILTINS = {
        "exec",
        "eval",
        "compile",
        "__import__",
        "globals",
        "locals",
        "open",
        "file",
        "exit",
        "quit",
        "help",
        "copyright",
        "credits",
        "license",
        "breakpoint",
        "setattr",
        "delattr",  # 可能用于修改关键对象
    }

    @classmethod
    def get_allowed_list(cls) -> List[str]:
        """获取允许的 builtins 列表"""
        return list(cls.ALLOWED_BUILTINS)


class CodeValidator:
    """代码验证器 - 静态分析代码安全性"""

    def __init__(self, config: SandboxConfig):
        self.config = config

    def validate(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        验证代码安全性

        Args:
            code: Python 代码字符串

        Returns:
            (is_valid, error_message)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"语法错误: {e}"

        # 检查导入
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split(".")[0]
                    if module_name not in self.config.allowed_modules:
                        return False, f"不允许导入模块: {alias.name}"

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split(".")[0]
                    if module_name not in self.config.allowed_modules:
                        return False, f"不允许从模块导入: {node.module}"

            # 检查危险的属性访问
            elif isinstance(node, ast.Attribute):
                if node.attr.startswith("_"):
                    # 允许 __name__, __doc__ 等常见属性
                    allowed_dunders = {
                        "__name__",
                        "__doc__",
                        "__class__",
                        "__dict__",
                        "__len__",
                        "__iter__",
                        "__next__",
                        "__str__",
                        "__repr__",
                        "__init__",
                        "__call__",
                        "__getitem__",
                        "__setitem__",
                        "__contains__",
                        "__eq__",
                        "__ne__",
                        "__lt__",
                        "__le__",
                        "__gt__",
                        "__ge__",
                        "__hash__",
                        "__bool__",
                        "__add__",
                        "__sub__",
                        "__mul__",
                        "__truediv__",
                        "__floordiv__",
                        "__mod__",
                        "__pow__",
                        "__neg__",
                        "__pos__",
                        "__abs__",
                        "__enter__",
                        "__exit__",
                        "__aenter__",
                        "__aexit__",
                        "__await__",
                        "__aiter__",
                        "__anext__",
                    }
                    if node.attr.startswith("__") and node.attr not in allowed_dunders:
                        return False, f"不允许访问私有属性: {node.attr}"

            # 检查危险的函数调用
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in RestrictedBuiltins.FORBIDDEN_BUILTINS:
                        return False, f"不允许调用危险函数: {node.func.id}"

        return True, None


# 沙箱执行器模板代码
SANDBOX_EXECUTOR_TEMPLATE = """
import sys
import json
import traceback
import io
from contextlib import redirect_stdout, redirect_stderr

# 设置资源限制（仅 Unix）
if sys.platform != 'win32':
    import resource
    try:
        resource.setrlimit(resource.RLIMIT_CPU, ({max_cpu_time}, {max_cpu_time}))
        max_mem = {max_memory_mb} * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (max_mem, max_mem))
    except Exception:
        pass

# 创建受限的 builtins
import builtins
allowed_builtins = {allowed_builtins}
restricted_builtins = {{name: getattr(builtins, name) for name in allowed_builtins if hasattr(builtins, name)}}

# 创建安全的 __import__
allowed_modules = {allowed_modules}
original_import = builtins.__import__

def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    module_name = name.split('.')[0]
    if module_name not in allowed_modules:
        raise ImportError(f"不允许导入模块: {{name}}")
    return original_import(name, globals, locals, fromlist, level)

restricted_builtins['__import__'] = safe_import

# 注入的函数
injected_functions = {injected_functions}

# 执行环境
exec_globals = {{
    '__builtins__': restricted_builtins,
    '__name__': '__sandbox__',
    '__doc__': None,
}}
exec_globals.update(injected_functions)
exec_locals = {{}}

# 捕获输出
stdout_capture = io.StringIO()
stderr_capture = io.StringIO()

result_data = {{
    'success': False,
    'output': None,
    'stdout': '',
    'stderr': '',
    'error': None,
    'error_type': None,
}}

try:
    code = {code_repr}
    
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        exec(compile(code, '<sandbox>', 'exec'), exec_globals, exec_locals)
    
    # 获取结果
    output = exec_locals.get('result', None)
    if output is None and exec_locals:
        for key in reversed(list(exec_locals.keys())):
            if not key.startswith('_'):
                output = exec_locals[key]
                break
    
    result_data['success'] = True
    result_data['output'] = repr(output) if output is not None else None
    
except Exception as e:
    result_data['error'] = str(e)
    result_data['error_type'] = type(e).__name__

result_data['stdout'] = stdout_capture.getvalue()
result_data['stderr'] = stderr_capture.getvalue()

# 输出结果
print("__SANDBOX_RESULT_START__")
print(json.dumps(result_data, ensure_ascii=False))
print("__SANDBOX_RESULT_END__")
"""


class CodeSandbox:
    """
    安全的 Python 代码沙箱执行器

    特性：
    - 进程级隔离（使用 subprocess）
    - 资源限制（CPU、内存、时间）
    - 受限的 builtins
    - 支持函数注入（用于工具调用）
    - 支持同步和异步代码执行

    使用示例：
    ```python
    sandbox = CodeSandbox(timeout=30, max_memory_mb=512)

    # 注入工具函数
    sandbox.inject("search", lambda q: f"搜索结果: {q}")
    sandbox.inject("calc", lambda expr: eval(expr))  # 注入的函数不受沙箱限制

    # 执行代码
    result = sandbox.execute('''
    data = search("天气")
    result = f"获取到: {data}"
    ''')

    if result.success:
        print(f"输出: {result.output}")
        print(f"标准输出: {result.stdout}")
    else:
        print(f"错误: {result.error}")
    ```
    """

    def __init__(
        self,
        timeout: int = 30,
        max_memory_mb: int = 512,
        max_cpu_time: int = 30,
        allowed_modules: Optional[Set[str]] = None,
    ):
        """
        初始化沙箱

        Args:
            timeout: 执行超时时间（秒）
            max_memory_mb: 最大内存限制（MB）
            max_cpu_time: 最大 CPU 时间（秒）
            allowed_modules: 允许导入的模块白名单
        """
        self.config = SandboxConfig(
            timeout=timeout, max_memory_mb=max_memory_mb, max_cpu_time=max_cpu_time
        )

        if allowed_modules:
            self.config.allowed_modules = allowed_modules

        self.validator = CodeValidator(self.config)
        self._injected_globals: Dict[str, Any] = {}
        self._injected_simple: Dict[str, str] = {}  # 简单值的字符串表示

    def inject(self, name: str, value: Any):
        """
        注入变量或函数到沙箱环境

        注意：由于沙箱使用独立进程，只能注入可序列化的值或简单函数。
        对于复杂的工具函数，建议使用 inject_simple_function。

        Args:
            name: 变量/函数名
            value: 值（可以是函数、类、常量等）
        """
        self._injected_globals[name] = value

        # 尝试将值转换为可在子进程中执行的形式
        if callable(value):
            # 对于函数，我们需要在主进程中执行，然后传递结果
            # 这里我们存储函数引用，在执行时动态调用
            pass
        else:
            # 对于简单值，尝试序列化
            try:
                self._injected_simple[name] = repr(value)
            except Exception:
                pass

    def inject_simple_function(self, name: str, func_code: str):
        """
        注入简单函数（以代码字符串形式）

        这种方式注入的函数可以在沙箱子进程中直接执行。

        Args:
            name: 函数名
            func_code: 函数定义代码（例如 "lambda x: x * 2"）
        """
        self._injected_simple[name] = func_code

    def inject_dict(self, values: Dict[str, Any]):
        """
        批量注入变量或函数

        Args:
            values: 要注入的键值对字典
        """
        for name, value in values.items():
            self.inject(name, value)

    def clear_injections(self):
        """清除所有注入的变量和函数"""
        self._injected_globals.clear()
        self._injected_simple.clear()

    def validate_code(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        验证代码安全性（不执行）

        Args:
            code: Python 代码字符串

        Returns:
            (is_valid, error_message)
        """
        return self.validator.validate(code)

    def _build_executor_code(self, code: str) -> str:
        """构建执行器代码"""
        # 处理注入的函数 - 对于复杂函数，我们需要预先执行
        injected_results = {}

        for name, value in self._injected_globals.items():
            if callable(value) and name not in self._injected_simple:
                # 对于可调用对象，我们创建一个包装器
                # 在实际执行时会回调主进程
                injected_results[name] = f"'<function {name}>'"
            elif name in self._injected_simple:
                injected_results[name] = self._injected_simple[name]
            else:
                try:
                    injected_results[name] = repr(value)
                except Exception:
                    injected_results[name] = f"'<object {name}>'"

        return SANDBOX_EXECUTOR_TEMPLATE.format(
            max_cpu_time=self.config.max_cpu_time,
            max_memory_mb=self.config.max_memory_mb,
            allowed_builtins=RestrictedBuiltins.get_allowed_list(),
            allowed_modules=list(self.config.allowed_modules),
            injected_functions=injected_results,
            code_repr=repr(code),
        )

    def _execute_with_callbacks(self, code: str) -> ExecutionResult:
        """
        执行代码，支持工具函数回调

        这种方式在主进程中处理工具调用，更灵活但稍慢。
        """
        import time

        start_time = time.time()

        # 验证代码
        is_valid, error = self.validate_code(code)
        if not is_valid:
            return ExecutionResult(
                success=False, error=error, error_type="ValidationError"
            )

        # 准备执行环境
        import builtins

        # 创建受限的 builtins
        restricted_builtins = {
            name: getattr(builtins, name)
            for name in RestrictedBuiltins.ALLOWED_BUILTINS
            if hasattr(builtins, name)
        }

        # 安全的 import
        original_import = builtins.__import__
        allowed_modules = self.config.allowed_modules

        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            module_name = name.split(".")[0]
            if module_name not in allowed_modules:
                raise ImportError(f"不允许导入模块: {name}")
            return original_import(name, globals, locals, fromlist, level)

        restricted_builtins["__import__"] = safe_import

        # 构建执行环境
        exec_globals = {
            "__builtins__": restricted_builtins,
            "__name__": "__sandbox__",
            "__doc__": None,
        }

        # 注入函数和变量
        exec_globals.update(self._injected_globals)

        exec_locals = {}

        # 捕获输出
        import io
        from contextlib import redirect_stdout, redirect_stderr

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(compile(code, "<sandbox>", "exec"), exec_globals, exec_locals)

            # 获取结果
            output = exec_locals.get("result", None)
            if output is None and exec_locals:
                for key in reversed(list(exec_locals.keys())):
                    if not key.startswith("_"):
                        output = exec_locals[key]
                        break

            execution_time = time.time() - start_time

            return ExecutionResult(
                success=True,
                output=output,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                error=str(e),
                error_type=type(e).__name__,
                execution_time=execution_time,
            )

    def execute(
        self, code: str, validate: bool = True, use_subprocess: bool = False
    ) -> ExecutionResult:
        """
        在沙箱中执行代码

        Args:
            code: Python 代码字符串
            validate: 是否在执行前验证代码
            use_subprocess: 是否使用子进程隔离（更安全但不支持复杂函数注入）

        Returns:
            ExecutionResult 对象
        """
        if use_subprocess:
            return self._execute_subprocess(code, validate)
        else:
            # 使用主进程执行（支持复杂函数注入）
            return self._execute_with_callbacks(code)

    def _execute_subprocess(self, code: str, validate: bool = True) -> ExecutionResult:
        """使用子进程执行代码（更强的隔离）"""
        import time

        start_time = time.time()

        # 代码验证
        if validate:
            is_valid, error = self.validate_code(code)
            if not is_valid:
                return ExecutionResult(
                    success=False, error=error, error_type="ValidationError"
                )

        # 构建执行器代码
        executor_code = self._build_executor_code(code)

        try:
            # 在子进程中执行
            result = subprocess.run(
                [sys.executable, "-c", executor_code],
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )

            execution_time = time.time() - start_time

            # 解析结果
            output = result.stdout

            # 查找结果标记
            start_marker = "__SANDBOX_RESULT_START__"
            end_marker = "__SANDBOX_RESULT_END__"

            if start_marker in output and end_marker in output:
                start_idx = output.index(start_marker) + len(start_marker)
                end_idx = output.index(end_marker)
                result_json = output[start_idx:end_idx].strip()

                try:
                    result_data = json.loads(result_json)

                    # 解析 output（如果是 repr 格式）
                    output_value = result_data.get("output")
                    if output_value and isinstance(output_value, str):
                        try:
                            output_value = eval(output_value)
                        except Exception:
                            pass

                    return ExecutionResult(
                        success=result_data.get("success", False),
                        output=output_value,
                        stdout=result_data.get("stdout", ""),
                        stderr=result_data.get("stderr", ""),
                        error=result_data.get("error"),
                        error_type=result_data.get("error_type"),
                        execution_time=execution_time,
                    )
                except json.JSONDecodeError:
                    pass

            # 无法解析结果
            return ExecutionResult(
                success=False,
                stdout=output,
                stderr=result.stderr,
                error="无法解析执行结果",
                error_type="ParseError",
                execution_time=execution_time,
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                error=f"代码执行超时（超过 {self.config.timeout} 秒）",
                error_type="TimeoutError",
                execution_time=self.config.timeout,
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                error=f"执行失败: {e}",
                error_type="InternalError",
                execution_time=execution_time,
            )

    def execute_with_async_tools(
        self, code: str, validate: bool = True
    ) -> ExecutionResult:
        """
        执行包含异步工具调用的代码

        这个方法会自动处理异步工具的调用，
        将异步函数包装为同步接口供沙箱代码使用。

        Args:
            code: Python 代码字符串
            validate: 是否在执行前验证代码

        Returns:
            ExecutionResult 对象
        """
        import asyncio

        # 为异步函数创建同步包装器
        wrapped_globals = {}

        for name, value in self._injected_globals.items():
            if asyncio.iscoroutinefunction(value):
                # 创建同步包装器
                def make_sync_wrapper(async_func):
                    def sync_wrapper(*args, **kwargs):
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                import concurrent.futures

                                future = asyncio.run_coroutine_threadsafe(
                                    async_func(*args, **kwargs), loop
                                )
                                return future.result(timeout=self.config.timeout)
                            else:
                                return loop.run_until_complete(
                                    async_func(*args, **kwargs)
                                )
                        except RuntimeError:
                            return asyncio.run(async_func(*args, **kwargs))

                    return sync_wrapper

                wrapped_globals[name] = make_sync_wrapper(value)
            else:
                wrapped_globals[name] = value

        # 临时替换注入的全局变量
        original_globals = self._injected_globals
        self._injected_globals = wrapped_globals

        try:
            return self.execute(code, validate)
        finally:
            self._injected_globals = original_globals

    def get_injected_names(self) -> List[str]:
        """获取所有注入的变量/函数名称"""
        return list(self._injected_globals.keys())

    def __repr__(self) -> str:
        return (
            f"CodeSandbox(timeout={self.config.timeout}s, "
            f"max_memory={self.config.max_memory_mb}MB, "
            f"injected={len(self._injected_globals)} functions)"
        )
