# From: https://github.com/janekb04/py2gpt/blob/main/main.py
# MIT License: https://github.com/janekb04/py2gpt/blob/main/LICENSE

import argparse
import ast
import inspect
import json
import docstring_parser
from typing import (
    Any,
    Callable,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    Optional,
    Tuple,
)
import types
import typing


def create_openai_function_description(func: ast.FunctionDef, func_obj):
    defaults: dict[str, Any] = {}
    for i, arg in enumerate(reversed(func.args.defaults)):
        if not isinstance(arg, ast.Constant):
            raise ValueError("Only constant default values are supported")
        defaults[func.args.args[-i - 1].arg] = arg.value
    if len(func.body) == 0 or not isinstance(func.body[0], ast.Expr):
        raise ValueError(
            f"Doc string not found in {func.body} for function {func.name}"
        )

    docstring = func.body[0].value.s

    try:
        parsed_docstring = docstring_parser.parse(docstring)
    except docstring_parser.ParseError as e:
        raise ValueError("Invalid function docstring format") from e

    func_name = func.name

    type_hints = get_type_hints(func_obj, globals(), defaults)

    args = [arg.arg for arg in func.args.args][1:]
    # First param is always RunContext
    doc_string_params = parsed_docstring.params[1:]
    for doc_param in doc_string_params:
        if doc_param.arg_name not in args:
            raise ValueError(
                f"Docstring describes non-existing argument: {doc_param.arg_name}"
            )
        if (
            "optional" in doc_param.description.lower()
            and doc_param.arg_name not in defaults
        ):
            raise ValueError(
                f"Docstring marks parameter {doc_param.arg_name} as optional but it doesn't have a default value"
            )
        if (
            "required" in doc_param.description.lower()
            and doc_param.arg_name in defaults
        ):
            raise ValueError(
                f"Docstring marks parameter {doc_param.arg_name} as required but it has a default value"
            )
        if (
            (doc_param.type_name is not None)
            and (doc_param.arg_name in type_hints)
            and (eval(doc_param.type_name) != type_hints[doc_param.arg_name])
        ):
            raise ValueError(
                f"Type hint {type_hints[doc_param.arg_name]} for parameter {doc_param.arg_name} doesn't match with it's description in docstring {eval(doc_param.type_name)}"
            )
        if (doc_param.type_name is None) and (doc_param.arg_name not in type_hints):
            raise ValueError(
                f"Docstring doesn't describe type of parameter {doc_param.arg_name}"
            )
        if (
            doc_param.description is None
            or doc_param.description.isspace()
            or doc_param.description == ""
        ):
            raise ValueError(
                f"Docstring doesn't describe parameter {doc_param.arg_name}"
            )
    doc_arg_names = [doc_param.arg_name for doc_param in doc_string_params]
    for arg in args:
        if arg not in doc_arg_names:
            raise ValueError(f"Docstring doesn't include argument: {arg}")

    if parsed_docstring.raises and (
        len(parsed_docstring.raises) != 1
        or parsed_docstring.raises[0].type_name != "None"
    ):
        raise ValueError("The function should not raise any exception")

    if (parsed_docstring.returns is not None) and (
        eval(parsed_docstring.returns.type_name) != type_hints.get("return")
    ):
        raise ValueError(
            f"Return type {type_hints.get('return')} doesn't match with it's description in docstring {eval(parsed_docstring.returns.type_name)}"
        )

    if (
        parsed_docstring.short_description is None
        or parsed_docstring.short_description.isspace()
        or parsed_docstring.short_description == ""
    ):
        raise ValueError("Docstring doesn't describe function")

    param_jsons = {}
    for param in doc_string_params:
        name = param.arg_name
        description = param.description
        t = eval(param.type_name) if param.type_name is not None else type_hints[name]
        type_descriptor, required = get_type_descriptor(t)
        param_jsons[name] = {"description": description, **type_descriptor}
        if not required:
            defaults[name] = None

    return {
        "type": "function",
        "function": {
            "name": func_name,
            "description": parsed_docstring.short_description,
            "parameters": {
                "type": "object",
                "properties": param_jsons,
                "required": [name for name in args if name not in defaults],
            },
        },
    }


def get_type_descriptor(t: type) -> Tuple[dict, bool]:
    required = True
    if get_origin(t) is Union and type(None) in get_args(t):
        required = False
        t = t.__args__[0]
    if t == str:
        return {"type": "string"}, required
    elif t == int:
        return {"type": "integer"}, required
    elif t == float or t == int | float:
        return {"type": "number"}, required
    elif t == bool:
        return {"type": "boolean"}, required
    elif t == type(None):
        return {"type": "null"}, required
    elif t == list:
        return {"type": "array"}, required
    elif t == dict:
        return {"type": "object"}, required
    elif type(t) == types.GenericAlias:
        if t.__origin__ == list:
            return {
                "type": "array",
                "items": get_type_descriptor(t.__args__[0])[0],
            }, required
        elif t.__origin__ == dict:
            if t.__args__[0] != str:
                raise ValueError(f"Unsupported type (JSON keys must be strings): { t}")
            return {
                "type": "object",
                "patternProperties": {".*": get_type_descriptor(t.__args__[1])},
            }, required
        else:
            raise ValueError(f"Unsupported type: {t}")
    elif type(t) == typing._LiteralGenericAlias:
        for arg in t.__args__:
            if type(arg) != type(t.__args__[0]):
                raise ValueError(f"Unsupported type (definite type is required): {t}")
        return {
            **get_type_descriptor(type(t.__args__[0])),
            "enum": t.__args__,
        }, required
    else:
        raise ValueError(f"Unsupported type: {t}")


def add_interpretation_args(func_dict: dict):
    func_dict["function"]["parameters"]["properties"]["interpretation"] = {
        "type": "string",
        "description": "A short <12 token description of what you are doing, formatted like 'Checking email...' or 'Creating calendar event...'",
    }
    func_dict["function"]["parameters"]["required"].append("interpretation")


def parse_assistant_module_code(decl: str) -> list[dict]:
    try:
        parsed = ast.parse(decl)
    except SyntaxError as e:
        raise ValueError(f"Invalid Python code: {str(e)}") from e

    namespace = {}
    exec("import typing\nimport types\nfrom typing import*\n" + decl, namespace)

    result: list[dict] = []
    for elem in parsed.body:
        try:
            if isinstance(elem, ast.FunctionDef) and not elem.name.startswith("_"):
                func_obj = namespace[elem.name]
                result.append(create_openai_function_description(elem, func_obj))
        except ValueError as e:
            raise ValueError(f"Error parsing function {elem.name}: {e}") from e

    # Add a fake "interpretation" argument to each function so we can
    # send to user.
    for func_dict in result:
        add_interpretation_args(func_dict)
    return result


def validate(decl: str):
    schema = parse_assistant_module_code(decl)
    print(json.dumps(schema, indent=2))


class callable_dict(dict):
    def __init__(self, func, func_dict):
        super().__init__(func_dict)
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


def gpt_callable(func: Callable):
    source = inspect.getsource(func)
    schema = create_openai_function_description(source)
    func_dict = schema[0]
    return callable_dict(func, func_dict)


def get_function_defs(module_file: str) -> list[dict]:
    with open(module_file, "rt") as aff:
        content = aff.read()
        function_schema = parse_assistant_module_code(content.decode("utf-8"))
        return function_schema


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, help="File to parse", required=True)
    args = parser.parse_args()
    with open(args.file, "r") as f:
        decl = f.read()
        validate(decl)
