import dis
from collections import deque
import inspect

class ExpressionReaction(object):
    def __init__(self, expression_to_monitor):
        self.expression_to_monitor = expression_to_monitor
        self.old_value = expression_to_monitor()
        self.on_change_expression = lambda expression_to_monitor, old_val, new_val: None

    def on_change(self, on_change_expression):
        self.on_change_expression = on_change_expression

    def call(self):
        new_value = self.expression_to_monitor()
        if self.old_value != new_value:
            self.on_change_expression(self.expression_to_monitor, self.old_value, new_value)
            self.old_value = new_value

class UnimplementedInstructionException(Exception):
    pass

class ObjectWrapper(object):
    def __init__(self, obj=None, base_obj=None, placeholder=False, buildin=False):
        self.obj = obj
        self.base_obj = base_obj
        self.placeholder = placeholder
        self.buildin = buildin

    def is_placeholder(self):
        return self.placeholder

    def is_build_in(self):
        return self.buildin

def placeaexpr(obj, attr_name, expression_reaction_object):
    if not hasattr(obj, '__listenon__'):
        if not hasattr(type(obj), "__aexprhandler__"):
            original = type(obj).__setattr__
            def new_set_attr(self, name, value):
                original(self, name, value)
                if name != "__aexprhandler__" and hasattr(self, '__aexprhandler__'):
                    type(self).__aexprhandler__(self, name, value)
            type(obj).__setattr__ = new_set_attr

            def execaexprhandler(self, name, value):
                if name != "__listenon__" and hasattr(self, '__listenon__'):
                    if name in self.__listenon__:
                        for listener in self.__listenon__[name]:
                            listener.call()
            type(obj).__aexprhandler__ = execaexprhandler
        obj.__listenon__ = {}

    if attr_name not in obj.__listenon__:
        obj.__listenon__[attr_name] = set()
    obj.__listenon__[attr_name].add(expression_reaction_object)


def aexpr(lambda_expression, globalvars, localvars=None):
    expression_reaction_object = ExpressionReaction(lambda_expression)

    #####
    # Install Op-Codes
    # Overview: http://unpyc.sourceforge.net/Opcodes.html
    # Currently supported: 60/112 (~54%)
    #####

    opcode_handler = [None] * 144 # 143 is the id of the last opcode (not all ids are used)
    def opcode(start, stop):
        def inner(func):
            for i in range(start, stop + 1):
                opcode_handler[i] = func
            return func
        return inner
    ignore = lambda inst, iq, os, vm: None

    opcode(0, 0)(ignore)
    opcode(1, 1)(lambda inst, iq, os, vm: os.pop())

    @opcode(2, 2)
    def rot_two_handler(inst, iq, os, vm):
        first_elem = os.pop()
        second_elem = os.pop()
        os.append(first_elem)
        os.append(second_elem)

    @opcode(3, 3)
    def rot_three_handler(inst, iq, os, vm):
        first_elem = os.pop() # 1
        second_elem = os.pop() # 2
        third_elem = os.pop() # 3
        os.append(first_elem) # 1
        os.append(third_elem) # 3
        os.append(second_elem) # 2

    @opcode(4, 4)
    def dup_top_handler(inst, iq, os, vm):
        elem = os.pop()
        os.append(elem)
        os.append(elem)

    @opcode(5, 5)
    def rot_four_handler(inst, iq, os, vm):
        first_elem = os.pop() # 1
        second_elem = os.pop() # 2
        third_elem = os.pop() # 3
        fourth_elem = os.pop() # 4
        os.append(first_elem) # 1
        os.append(fourth_elem) # 4
        os.append(third_elem) # 3
        os.append(second_elem) # 2

    opcode(9, 9)(ignore)

    @opcode(10, 15)
    def unary_op_handler(inst, iq, os, vm):
        os.pop()
        os.append(ObjectWrapper(placeholder=True))

    @opcode(19, 29)
    def binary_op_handler(inst, iq, os, vm):
        os.pop()
        os.pop()
        os.append(ObjectWrapper(placeholder=True))
    opcode(55, 59)(binary_op_handler)
    opcode(62, 67)(binary_op_handler)
    opcode(68, 68)(unary_op_handler)

    opcode(70, 70)(ignore)
    opcode(71, 71)(unary_op_handler)
    opcode(72, 72)(ignore)

    opcode(75, 79)(binary_op_handler)

    opcode(80, 80)(ignore)
    opcode(83, 83)(ignore)
    opcode(87, 87)(ignore)
    opcode(93, 93)(ignore)
    opcode(100, 100)(lambda inst, iq, os, vm: os.append(ObjectWrapper(placeholder=True)))

    @opcode(106, 106)
    def load_attr_handler(inst, iq, os, vm):
        attr_name = inst.argval
        obj = get_obj_from_objectstack(os, inst)
        placeaexpr(obj, attr_name, expression_reaction_object)
        os.append(ObjectWrapper(obj=getattr(obj, attr_name), base_obj=obj))

    opcode(107, 107)(binary_op_handler)
    opcode(113, 115)(ignore)

    @opcode(116, 116)
    def load_global_handler(inst, iq, os, vm):
        if inst.argval in globalvars: # build ins are for example not in globals()
            os.append(ObjectWrapper(obj=globalvars[inst.argval]))
        else:
            os.append(ObjectWrapper(buildin=True))

    opcode(119, 122)(ignore)
    opcode(124, 124)(lambda inst, iq, os, vm: os.append(vm[inst.argval]))

    @opcode(125, 125)
    def store_fast_handler(inst, iq, os, vm):
        vm[inst.argval] = os.pop()
    opcode(126, 126)(lambda inst, iq, os, vm: vm.pop(inst.argval, None))

    @opcode(131, 131)
    def call_function_handler(inst, iq, os, vm):
        # Get arguments
        func_args = []
        if inst.argval > 0:
            func_args = os[-inst.argval:]
            os = os[:-inst.argval]

        wrapper = os.pop()
        if not wrapper.is_build_in():
            func = get_obj_from_wrapper(wrapper, inst)
            if inspect.isclass(func):
                os.append(ObjectWrapper(placeholder=True))
            else:
                params = inspect.getfullargspec(func)
                localvars = {}
                for i in range(inst.argval, 0, -1):
                    localvars[params.args[i]] = func_args[i-1]

                os.append(process_function(func.__code__, wrapper.base_obj, localvars))
        else:
            os.append(ObjectWrapper(placeholder=True))

    opcode(136, 136)(lambda inst, iq, os, vm: os.append(vm[inst.argval]))

    #####
    # Static Analysis
    #####

    def get_obj_from_objectstack(os, inst):
        wrapper = os.pop()
        return get_obj_from_wrapper(wrapper, inst)

    def get_obj_from_wrapper(wrapper, inst):
        if wrapper.is_placeholder():
            print("Warning: Access to Placeholder isn't supported (Instruction: " + str(inst) + ")")
        return wrapper.obj

    def process_function(function_code, self, localvars=None):
        instruction_queue = deque()
        object_stack = []
        variable_mapping = {}
        if not localvars is None:
            for varname in localvars:
                obj = localvars[varname]
                if not isinstance(obj, ObjectWrapper):
                    obj = ObjectWrapper(obj=obj)
                variable_mapping[varname] = obj
        if "self" not in variable_mapping:
            variable_mapping["self"] = ObjectWrapper(obj=self)

        instruction_queue.extend(dis.get_instructions(function_code))

        while instruction_queue:
            inst = instruction_queue.popleft()
            # print(instruction)
            if opcode_handler[inst.opcode] != None:
                opcode_handler[inst.opcode](inst, instruction_queue, object_stack, variable_mapping)
            else:
                raise UnimplementedInstructionException("Unimplemented Instruction: " + str(inst))
        return object_stack.pop()

    process_function(lambda_expression.__code__, None, localvars)

    return expression_reaction_object
