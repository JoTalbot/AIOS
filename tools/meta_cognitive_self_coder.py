# meta_cognitive_self_coder.py
from dataclasses import dataclass
from typing import List, Dict
import os

@dataclass
class Code:
    """Represents a piece of code."""
    name: str
    content: str

def generate_code(name: str, content: str) -> Code:
    """
    Generates a piece of code.

    Args:
    - name (str): The name of the code.
    - content (str): The content of the code.

    Returns:
    - Code: A Code object.
    """
    return Code(name, content)

def get_code_from_file(file_path: str) -> Code:
    """
    Reads a code from a file.

    Args:
    - file_path (str): The path to the file.

    Returns:
    - Code: A Code object.

    Raises:
    - FileNotFoundError: If the file does not exist.
    - OSError: If there is an error reading the file.
    """
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            return Code(os.path.basename(file_path), content)
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except OSError as e:
        print(f"Error reading file: {e}")

def get_code_from_string(content: str) -> Code:
    """
    Generates a piece of code from a string.

    Args:
    - content (str): The content of the code.

    Returns:
    - Code: A Code object.
    """
    return Code('string_code', content)

def get_all_codes_in_directory(directory_path: str) -> List[Code]:
    """
    Gets all codes in a directory.

    Args:
    - directory_path (str): The path to the directory.

    Returns:
    - List[Code]: A list of Code objects.

    Raises:
    - FileNotFoundError: If the directory does not exist.
    - OSError: If there is an error reading the directory.
    """
    try:
        codes = []
        for file in os.listdir(directory_path):
            file_path = os.path.join(directory_path, file)
            if os.path.isfile(file_path):
                codes.append(get_code_from_file(file_path))
        return codes
    except FileNotFoundError as e:
        print(f"Directory not found: {e}")
    except OSError as e:
        print(f"Error reading directory: {e}")

def get_code_from_dict(code_dict: Dict[str, str]) -> Code:
    """
    Generates a piece of code from a dictionary.

    Args:
    - code_dict (Dict[str, str]): A dictionary containing the code.

    Returns:
    - Code: A Code object.
    """
    return Code('dict_code', code_dict['content'])

__all__ = ['generate_code', 'get_code_from_file', 'get_code_from_string', 'get_all_codes_in_directory', 'get_code_from_dict']

if __name__ == '__main__':
    import unittest

    class TestMetaCognitiveSelfCoder(unittest.TestCase):
        def test_generate_code(self):
            code = generate_code('test_code', 'print("Hello World!")')
            self.assertEqual(code.name, 'test_code')
            self.assertEqual(code.content, 'print("Hello World!")')

        def test_get_code_from_file(self):
            code = get_code_from_file('test.py')
            self.assertEqual(code.name, 'test.py')
            self.assertEqual(code.content, 'print("Hello World!")')

        def test_get_code_from_string(self):
            code = get_code_from_string('print("Hello World!")')
            self.assertEqual(code.name, 'string_code')
            self.assertEqual(code.content, 'print("Hello World!")')

        def test_get_all_codes_in_directory(self):
            codes = get_all_codes_in_directory('codes')
            self.assertGreater(len(codes), 0)

        def test_get_code_from_dict(self):
            code_dict = {'name': 'dict_code', 'content': 'print("Hello World!")'}
            code = get_code_from_dict(code_dict)
            self.assertEqual(code.name, 'dict_code')
            self.assertEqual(code.content, 'print("Hello World!")')

    unittest.main(argv=[os.path.basename(__file__)])