# Active-Expressions in Python

Active Expression Implementation for Python using static-byte-code analysis.

## Installation

To use Active Expression you need at least Python 3.4.
To install the package, you can run the following command:

```
pip3 install git+https://github.com/active-expressions/active-expressions-static-python
```

Otherwise you can clone this repository and import the `aexpr.py` file in the subfoler `aexpr`.

## Usage

First you have to import the library:

```
from aexpr import aexpr
```

Afterwards you can use the method `aexpr` in your program.

For the following example lets assume we have the following class:

```
class Example:
    def __init__(self):
        self.f = 5
```

Let `tmp` be an instance of this class:

```
tmp = Example()
```

Now we can call the `aexpr`-method:

```
aexpr(<expression>, <globalscope>, <localscope>).on_change(<reaction>)
aexpr(lambda: tmp.f, globals(), locals()).on_change(lambda observable, old_value, new_value: doSth())
```

The method `aexpr` requires a lambda expression, which will be analysed as described in the [presentation](https://github.com/active-expressions/active-expressions-static-python/blob/master/presentation/presentation.pdf).
This lambda expression is the monitored expression.
All fields of objects with influence on the result of this expression are monitored.
See some more examples for this expression in the [Example.ipynb](https://github.com/active-expressions/active-expressions-static-python/blob/master/Examples.ipynb)-notebook.

The method also requires the global and maybe also the local scope since the lambda expression can take objects from there.
Just hand in `globals()` (required) and `locals()` (optional).

The method returns a `ExpressionReaction` object.
This object has a `on_change()`-method, which takes a lambda expression as argument.
This on-change expression will be called every time when one of the detected dependencies changes.

The on-change lambda expression gets three arguments.

 - `observable` is the monitored expression itself
 - `old_value` is the old value of the monitored expression
 - `new_value` is the new value of the monitored expression

**Be careful:** To get the old and the new value the expression will be executed twice. It should be side-effect free and fast.

You can find more examples in the [Example.ipynb](https://github.com/active-expressions/active-expressions-static-python/blob/master/Examples.ipynb)-notebook.
If you want to see this tutorial visually you can watch the [screencast](https://github.com/active-expressions/active-expressions-static-python/tree/master/screencast).

## Implementation

This library performs a static byte-code analysis of the expression and all nested methods.
Therefore it simulates an object-stack and an own variable mapping and processes all byte-code instruction itself.
Currently around 54% of all byte-code instructions are supported.
See the contribution section if you want to increase this number ;)

An example for the analysis is shown in the [presentation](https://github.com/active-expressions/active-expressions-static-python/blob/master/presentation/presentation.pdf).

## Limitations

This library does not support data structures like lists, sets, maps, ...
It also can not monitor local variables.
See some more limitations in the [presentation](https://github.com/active-expressions/active-expressions-static-python/blob/master/presentation/presentation.pdf).

## Contribution

If you have some complex expression to monitor it can happen that you get an `UnimplementedInstructionException`.
Afterwards you see the unsupported byte-code-instruction. Feel free to create pull request to this repository to support that instruction.
