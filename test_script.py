#!/usr/bin/env python3
"""A simple test script to debug."""


def greet(name):
    message = f"Hello, {name}!"
    return message


def calculate(a, b):
    total = a + b
    doubled = total * 2
    return doubled


def main():
    names = ["Alice", "Bob", "Charlie"]

    for name in names:
        greeting = greet(name)
        print(greeting)

    result = calculate(10, 20)
    print(f"Result: {result}")

    data = {"x": 1, "y": 2, "z": 3}
    for key, value in data.items():
        print(f"{key} = {value}")


if __name__ == "__main__":
    main()
