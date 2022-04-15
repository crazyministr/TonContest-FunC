data_test_function = """
[int, tuple, cell, tuple, int] test_op={op_rn}_data() method_id({method_id}) {{
    int function_selector = 0;
    ;;                             op  key  shit     value
    cell message = message_packing({op},  {key}, {shift}, {value});
    tuple stack = unsafe_tuple([0, 0, message, message.begin_parse()]); ;; stack that will be passed to function

    {code}
}}
"""
test_function = """
_ test_op={op_rn}(int exit_code, cell data, tuple stack, cell actions, int gas) method_id({method_id}) {{
    throw_if(100, exit_code != 0); ;; test need to be passed
    throw_if(102, gas > 1000000); ;; check if gas usage is not so big
}}
"""

data_test_get_function = """
;; 127977 get_key
;; GET method test
[int, tuple, cell, tuple, int] test_get_key{i}_data() method_id({method_id}) {{
    int function_selector = 127977;  ;; function to run (127977 is get_key)
    ;;                                      key   data
    return [function_selector, unsafe_tuple([{key}]), get_prev_c4(), get_c7(), null()];
}}
"""

test_get_function_not_found = """
_ test_get_key_{i}(int exit_code, cell data, tuple stack, cell actions, int gas) method_id({method_id}) {{
    throw_if(103, exit_code != 404); ;; test need to be passed
}}
"""

test_get_function_found = """
_ test_get_key{i}(int exit_code, cell data, tuple stack, cell actions, int gas) method_id({method_id}) {{
    throw_if(103, exit_code != 0); ;; test need to be passed

    var valid_until = first(stack);
    var value = second(stack);
    throw_if(104, {valid_until});
    throw_if(105, value~load_uint(32) != {value});
}}
"""

# recv_internal_function_selector = 0
# get_key_function_selector = 127977
method_id = 0

# requests_op_1 = 10
# requests_op_2 = 1
# requests_get_key = 10
shift = int(1e6)

"""
;; Each test function must specify method_id
;; Test functions method_id need to started from 0

;; Each test functions must to be in pairs
;; First function expect nothing in arguments
;; But need to return:
;;        function selector - which function to test, e.g. 0 for recv_internal, -1 recv_external, 85143 for seqno, and so on
;;        tuple - stack values needed to be passed to function in tuple
;;        c4 cell - start data of smart contract
;;        c7 tuple / null
;;        gas limit integer / null
"""

import time
from urllib import request

# requests = [
#     (1, 1, shift, 13),
#     (1, 2, -shift, 21),
#     (3, 1),
#     (3, 2),
#     (2, ),
#     (3, 1),
#     (3, 2),
# ]
# requests = [
#     # op  key        value
#     ( 1,  1,  shift, 13),
#     ( 3,  1),
#     ( 1,  2,  shift, 13),
#     ( 3,  2),
#     ( 3,  1),
# ]

# with replace
# requests = [
#     (1, 1, shift, 13),
#     (1, 1, shift, 21),
#     (3, 1),
# ]

# requests = [
#     # op  key        value
#     ( 1,  1,  shift, 13),
#     ( 1,  2,  shift, 14),
#     ( 2, ),
#     ( 1,  3,  -shift, 15),
#     ( 3, 1),  # get key
#     ( 3, 2),  # get key
#     ( 3, 3),  # get key
#     ( 2, ),   # gas = 10344
#     ( 3, 1),  # get key
#     ( 3, 2),  # get key
#     ( 3, 3),  # get key
# ]

# requests = [
#     (1, key, -shift, key)
#     for key in range(100)
# ]
# requests.extend([
#     (2, ),
#     (3, 1)
# ])
# requests.extend([
#     (3, key)
#     for key in range(100)
# ])

import random

requests = []
for i in range(100):
    op = random.randint(1, 3)
    if op == 1:
        requests.append((1, random.randint(1, 5), shift * (1 if random.randint(0, 1) == 0 else -1), random.randint(0, 100)))
    if op == 2:
        requests.append((2,))
    if op == 3:
        requests.append((3, random.randint(1, 5)))

# requests = [
#     (3, 1)
# ]

if_is_first_test = """
    cell data = begin_cell().end_cell(); ;; initial data of contract
    return [function_selector, stack, data, get_c7(), null()];
"""
if_is_not_first_test = """
    return [function_selector, stack, get_prev_c4(), get_c7(), null()];
"""

result = [
"""
cell message_packing(int op, int key, int valid_until_shift, int value) inline method_id {
    cell msg_body_cell = begin_cell().store_uint(value, 32).end_cell();
    slice msg_body = msg_body_cell.begin_parse();
    cell message = begin_cell()                           ;; external message body
            .store_uint(op, 32)                           ;; op
            .store_uint(0, 64)                            ;; query_id
            .store_uint(key, 256)                         ;; key
            .store_uint(now() + valid_until_shift, 64)    ;; unixtime (valid_until)
            .store_slice(msg_body)                        ;; value
         .end_cell();
    return message;
}
"""
]

was_first_op_test = False

storage = {}  # {key: (valid_until, value, '+' or '-')}

for i, req in enumerate(requests):
    if req[0] == 1:
        op, key, time_shift, value = req
        result.append(data_test_function.format(
            op_rn=f'op={op}_{i}r',
            method_id=method_id,
            op=op,
            key=key,
            shift=time_shift if time_shift > 0 else f'- {-time_shift}',
            value=value,
            code=if_is_not_first_test if was_first_op_test else if_is_first_test
        ))
        result.append(test_function.format(
            op_rn=f'op={op}_{i}r',
            method_id=method_id + 1,
        ))

        storage[key] = (int(time.time()) + time_shift, value, '+' if time_shift > 0 else '-')

    if req[0] == 2:
        result.append(data_test_function.format(
            op_rn=f'op=2_{i}r',
            method_id=method_id,
            op=2,
            key=0,
            shift=0,
            value=0,
            code=if_is_not_first_test if was_first_op_test else if_is_first_test
        ))
        result.append(test_function.format(
            op_rn=f'op=2_{i}r',
            method_id=method_id + 1,
        ))

        storage = {
            k: v
            for k, v in storage.items()
            if v[0] > int(time.time())
        }

    if req[0] == 3:
        op, key = req
        result.append(data_test_get_function.format(
            i=i,
            method_id=method_id,
            key=key,
        ))

        v = storage.get(key)
        if v is not None:
            result.append(test_get_function_found.format(
                i=i,
                method_id=method_id + 1,
                valid_until=f'now() {v[2]} {shift} - valid_until > 10',
                value=v[1]
            ))
        else:
            result.append(test_get_function_not_found.format(
                i=i,
                method_id=method_id + 1,
            ))

    method_id += 2

    if 1 <= req[0] <= 2:
        was_first_op_test = True

    result.append('\n;;' + '=' * 30 + '\n')


print(''.join(result))
