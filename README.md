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

If you want to see this tutorial visually you can watch the [screencast](https://github.com/active-expressions/active-expressions-static-python/tree/master/screencast).

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

## Implementation

This library analysis the given lambda expression and all nested methods to find all dependencies of the result of the lambda expression.
Dependencies of an expression are in this case all fields which are used in the expression or in nested methods.
**Example** (from the [presentation](https://github.com/active-expressions/active-expressions-static-python/blob/master/presentation/presentation.pdf)):

```
class Example:
  def __init__(self):
    self.f = 5
    self.g = 10

  def method(self):
    t = self.f + 2
    return t + self.get_g()

  def get_g(self):
    return self.g

tmp = Example()
aexpr(lambda: tmp.method())
```

The dependencies are `self.f` and `self.g` (from object `tmp`).
To be able to monitor the dependencies of the expression, we have to find them first.

## Step 1: Find the dependencies

Therefore this library performs a static byte-code analysis of the expression and all nested methods.
It converts the binary byte-code of the expression and all nested methods with the library [`dis`](https://docs.python.org/2/library/dis.html).
Afterwards it simulates an object-stack and an own variable mapping and processes all byte-code instruction itself.

**Short Example** (the complete one is in the [presentation](https://github.com/active-expressions/active-expressions-static-python/blob/master/presentation/presentation.pdf)):
```
...
LOAD_FAST (self)
LOAD_ATTR (f)
LOAD_CONST (2)
...
```

`LOAD_FAST` pushes an object (`self` in this case which is equals to `tmp`) to the object stack.
Afterwards `LOAD_ATTR` pulls the top of stack object and gets the attribute `f` from this attribute.
Now we found a dependency of the expression.
More general: **Always when we process a `LOAD_ATTR` instruction we find a dependency.**
The attribute will be pushed on the stack and the simulation continues with `LOAD_CONST`.
The [`aexpr`-method](https://github.com/active-expressions/active-expressions-static-python/blob/master/aexpr/aexpr.py#L72) performs this static byte-code analysis.

This implementation performs not all byte-codes in all details.
It abstracts some of the instructions.
An addition for example only takes two elements from the object stack and pushes a placeholder on this since we do not really care about the result.
A multiplication does the same.
Thats the reason why all elements on our own object stack are wrapped in an [ObjectWrapper](https://github.com/active-expressions/active-expressions-static-python/blob/master/aexpr/aexpr.py#L29), which can be an real object or a placeholder.

## Step 2: Monitor the dependencies

When we found the dependencies we have to monitor them to be able to trigger if something changes.
For all dependencies (attribute of a object) we modify the `__setattr__`-method of the object, which will be called when setting a attribute of that object.
We install a hook in that `__setattr__`-method which checks if we monitor that specific attribute and calls all triggers if so.
The [method `placeaexpr`](https://github.com/active-expressions/active-expressions-static-python/blob/master/aexpr/aexpr.py#L46) installs these hooks.

Currently around 54% of all byte-code instructions are supported.
See the contribution section if you want to increase this number ;)

The full example for this analysis is shown in the [presentation](https://github.com/active-expressions/active-expressions-static-python/blob/master/presentation/presentation.pdf).

## Limitations

This library has the few following limitations. Feel free to contribute and fix these limitations:

 - **Lists, Sets, Maps:** Datastructures are not supported so far. Means if you store a dependency in a list and access the an attribute later, you can not monitor on that attribute.
 - **Local Variables:** Local Variables are not instrumentable since they do not have a `__setattr__` or something else. Only fields of objects are instrumentable.
 - **External Resources:** Monitoring if a server is available or a file exists would require to poll this information repeatedly. This is not supported.
 - **Transactions:** Each time a dependency changes all triggers are triggered. Its not possible to pause this to change more attributes at once.
 - **Other language features:** Not supported are for examples *exceptions* and *closures*; *concurreny*, *asynchrony* and *meta-programming* can cause issues as well.

You can find some code examples for some of them in the [presentation](https://github.com/active-expressions/active-expressions-static-python/blob/master/presentation/presentation.pdf).

## Contribution

If you have some complex expression to monitor it can happen that you get an `UnimplementedInstructionException`.
This means that you try to perform an instruction which is not so far supported.
Afterwards you see the unsupported byte-code-instruction.
Feel free to create pull request to this repository to support that instruction.

To support a new instruction you have to modify the content of the `aexpr`-method.
Call the method `opcode` once with the new supported op-codes of the instruction and call the result with a method which performs the required actions.
Therefore you get the instruction, the rest of the instruction queue, the object stack and the variable mapping as parameters.
There are already a lot of examples for this in this method.
