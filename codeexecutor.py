# codeexecutor.py
import subprocess
import tempfile
import os
import json
from datetime import datetime

class CodeExecutor:
    """Code execution engine for various programming languages"""
    
    SUPPORTED_LANGUAGES = {
        'python': {
            'extension': '.py',
            'command': ['python'],
            'timeout': 30
        },
        'javascript': {
            'extension': '.js',
            'command': ['node'],
            'timeout': 30
        },
        'java': {
            'extension': '.java',
            'command': ['javac', '{file}', '&&', 'java', '{classname}'],
            'timeout': 45,
            'compile_first': True
        },
        'cpp': {
            'extension': '.cpp',
            'command': ['g++', '{file}', '-o', '{output}', '&&', '{output}'],
            'timeout': 45,
            'compile_first': True
        },
        'c': {
            'extension': '.c',
            'command': ['gcc', '{file}', '-o', '{output}', '&&', '{output}'],
            'timeout': 45,
            'compile_first': True
        }
    }
    
    @classmethod
    def execute_code(cls, code, language, input_data=""):
        """Execute code in the specified language"""
        if language not in cls.SUPPORTED_LANGUAGES:
            return {
                'success': False,
                'output': '',
                'error': f'Language "{language}" not supported',
                'execution_time': 0
            }
        
        lang_config = cls.SUPPORTED_LANGUAGES[language]
        
        try:
            start_time = datetime.now()
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=lang_config['extension'],
                delete=False,
                encoding='utf-8'
            ) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            try:
                if language == 'python':
                    result = cls._execute_python(temp_file_path, input_data, lang_config['timeout'])
                elif language == 'javascript':
                    result = cls._execute_javascript(temp_file_path, input_data, lang_config['timeout'])
                elif language == 'java':
                    result = cls._execute_java(temp_file_path, input_data, lang_config['timeout'])
                elif language in ['cpp', 'c']:
                    result = cls._execute_compiled(temp_file_path, language, input_data, lang_config['timeout'])
                else:
                    result = {
                        'success': False,
                        'output': '',
                        'error': f'Execution not implemented for {language}',
                        'execution_time': 0
                    }
                
                end_time = datetime.now()
                result['execution_time'] = (end_time - start_time).total_seconds()
                
                return result
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': f'Execution error: {str(e)}',
                'execution_time': 0
            }
    
    @classmethod
    def _execute_python(cls, file_path, input_data, timeout):
        """Execute Python code"""
        try:
            process = subprocess.Popen(
                ['python', file_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(file_path)
            )
            
            stdout, stderr = process.communicate(input=input_data, timeout=timeout)
            
            return {
                'success': process.returncode == 0,
                'output': stdout,
                'error': stderr,
                'return_code': process.returncode
            }
            
        except subprocess.TimeoutExpired:
            process.kill()
            return {
                'success': False,
                'output': '',
                'error': 'Execution timed out',
                'return_code': -1
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'return_code': -1
            }
    
    @classmethod
    def _execute_javascript(cls, file_path, input_data, timeout):
        """Execute JavaScript code"""
        try:
            # For Node.js, we need to modify the code to handle input
            if input_data:
                # Create a wrapper that provides input via process.stdin
                wrapper_code = f"""
const originalCode = require('fs').readFileSync('{file_path}', 'utf8');
const inputData = `{input_data}`;

// Mock readline for simple input
let inputLines = inputData.split('\\n');
let inputIndex = 0;

global.prompt = function(text) {{
    if (text) process.stdout.write(text);
    return inputLines[inputIndex++] || '';
}};

// Execute the original code
eval(originalCode);
"""
                with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as wrapper_file:
                    wrapper_file.write(wrapper_code)
                    wrapper_path = wrapper_file.name
                
                process = subprocess.Popen(
                    ['node', wrapper_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                try:
                    os.unlink(wrapper_path)
                except:
                    pass
            else:
                process = subprocess.Popen(
                    ['node', file_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=os.path.dirname(file_path)
                )
            
            stdout, stderr = process.communicate(timeout=timeout)
            
            return {
                'success': process.returncode == 0,
                'output': stdout,
                'error': stderr,
                'return_code': process.returncode
            }
            
        except subprocess.TimeoutExpired:
            process.kill()
            return {
                'success': False,
                'output': '',
                'error': 'Execution timed out',
                'return_code': -1
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'return_code': -1
            }
    
    @classmethod
    def _execute_java(cls, file_path, input_data, timeout):
        """Execute Java code"""
        try:
            # Extract class name from file
            dir_path = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            class_name = filename[:-5]  # Remove .java extension
            
            # Compile
            compile_process = subprocess.Popen(
                ['javac', file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=dir_path
            )
            
            compile_stdout, compile_stderr = compile_process.communicate(timeout=timeout)
            
            if compile_process.returncode != 0:
                return {
                    'success': False,
                    'output': compile_stdout,
                    'error': f'Compilation error: {compile_stderr}',
                    'return_code': compile_process.returncode
                }
            
            # Run
            run_process = subprocess.Popen(
                ['java', class_name],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=dir_path
            )
            
            stdout, stderr = run_process.communicate(input=input_data, timeout=timeout)
            
            # Clean up class file
            try:
                os.unlink(os.path.join(dir_path, f'{class_name}.class'))
            except:
                pass
            
            return {
                'success': run_process.returncode == 0,
                'output': stdout,
                'error': stderr,
                'return_code': run_process.returncode
            }
            
        except subprocess.TimeoutExpired:
            try:
                compile_process.kill()
            except:
                pass
            try:
                run_process.kill()
            except:
                pass
            return {
                'success': False,
                'output': '',
                'error': 'Execution timed out',
                'return_code': -1
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'return_code': -1
            }
    
    @classmethod
    def _execute_compiled(cls, file_path, language, input_data, timeout):
        """Execute C/C++ code"""
        try:
            dir_path = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            executable_name = filename[:filename.rfind('.')] + '.exe' if os.name == 'nt' else filename[:filename.rfind('.')]
            executable_path = os.path.join(dir_path, executable_name)
            
            # Compile
            compiler = 'g++' if language == 'cpp' else 'gcc'
            compile_process = subprocess.Popen(
                [compiler, file_path, '-o', executable_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=dir_path
            )
            
            compile_stdout, compile_stderr = compile_process.communicate(timeout=timeout)
            
            if compile_process.returncode != 0:
                return {
                    'success': False,
                    'output': compile_stdout,
                    'error': f'Compilation error: {compile_stderr}',
                    'return_code': compile_process.returncode
                }
            
            # Run
            run_process = subprocess.Popen(
                [executable_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=dir_path
            )
            
            stdout, stderr = run_process.communicate(input=input_data, timeout=timeout)
            
            # Clean up executable
            try:
                os.unlink(executable_path)
            except:
                pass
            
            return {
                'success': run_process.returncode == 0,
                'output': stdout,
                'error': stderr,
                'return_code': run_process.returncode
            }
            
        except subprocess.TimeoutExpired:
            try:
                compile_process.kill()
            except:
                pass
            try:
                run_process.kill()
            except:
                pass
            return {
                'success': False,
                'output': '',
                'error': 'Execution timed out',
                'return_code': -1
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'return_code': -1
            }

# Test the code executor
if __name__ == "__main__":
    # Test Python execution
    python_code = """
print("Hello, World!")
name = input("Enter your name: ")
print(f"Hello, {name}!")
"""
    
    result = CodeExecutor.execute_code(python_code, 'python', 'Alice')
    print("Python Result:", json.dumps(result, indent=2))
    
    # Test JavaScript execution
    js_code = """
console.log("Hello from JavaScript!");
console.log("2 + 2 =", 2 + 2);
"""
    
    result = CodeExecutor.execute_code(js_code, 'javascript')
    print("JavaScript Result:", json.dumps(result, indent=2))