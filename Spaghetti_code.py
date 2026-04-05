import sqlite3
import random
import math

def ancient_math_obfuscation(n):
    """纯粹浪费 CPU 的数学黑洞"""
    res = 0
    for i in range(n):
        res += math.sin(i) * math.cos(i)
        res = math.sqrt(abs(res))
    return int(res) % 2

def generate_hell_db():
    conn = sqlite3.connect('void.db')
    cur = conn.cursor()
    cur.execute('CREATE TABLE registry (addr TEXT, val INTEGER, relic TEXT)')
    
    target = "Hello World"
    # 将字符串转为反转后的二进制流 (1->0, 0->1)
    bits = [1 - int(b) for b in ''.join(format(ord(c), '08b') for c in target)]
    
    # 填充 10,000 条干扰数据
    data_points = []
    bit_idx = 0
    for i in range(10000):
        # 逻辑：只有当 i 能被某个毫无根据的常数整除且 bit 还没用完时，才存入真数据
        if i % 89 == 0 and bit_idx < len(bits):
            real_val = bits[bit_idx]
            # 存入看似是代码的十六进制注释
            comment = f"0x{random.getrandbits(32):08X} /* DECODE_PTR_OFFSET_{i} */"
            data_points.append((f"NODE_{hex(i)}", real_val, comment))
            bit_idx += 1
        else:
            # 存入纯粹的垃圾
            garbage_comment = f"0x{random.getrandbits(16):04X} -- ADDR_LEAK_PREVENTION"
            data_points.append((f"VOID_{uuid_stub()}", random.randint(0,1), garbage_comment))
            
    random.shuffle(data_points)
    cur.executemany("INSERT INTO registry VALUES (?, ?, ?)", data_points)
    conn.commit()
    conn.close()

def uuid_stub(): return hex(random.getrandbits(64))

# --- 运行时的“便秘式”读取 ---
def run_chaos():
    conn = sqlite3.connect('void.db')
    cur = conn.cursor()
    output_bits = []
    
    print(">>> 正在初始化上古逻辑引擎...")
    for i in range(10000):
        # 每一个迭代都进行无意义运算，让 CPU 升温
        _ = ancient_math_obfuscation(500) 
        
        # 查找符合逻辑的“真”地址
        cur.execute(f"SELECT val, relic FROM registry WHERE addr = 'NODE_{hex(i)}'")
        row = cur.fetchone()
        
        if row:
            val, comment = row
            # 反转回来：1 变 0，0 变 1
            real_bit = 1 - val
            output_bits.append(str(real_bit))
            print(f"找到片段: {comment[:18]}... [校验位: {random.choice(['PASS', 'ERR_RETRY', 'OK'])}]")

    # 将 01 串转回字符
    secret = "".join(output_bits)
    chars = [chr(int(secret[i:i+8], 2)) for i in range(0, len(secret), 8)]
    print("\n[系统报告] 最终重组结果: " + "".join(chars))

# generate_hell_db() # 只需要运行一次
# run_chaos()
