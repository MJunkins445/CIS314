import random
import secrets
from collections import Counter
from time import perf_counter
from typing import Callable, List, Tuple

# RNG 
def fill_with_random(x: int, lo: int, hi: int) -> List[int]:
    return [random.randint(lo, hi) for _ in range(x)]

def fill_with_secrets(x: int, lo: int, hi: int) -> List[int]:
    span = hi - lo + 1
    return [secrets.randbelow(span) + lo for _ in range(x)]

def counts(a: List[int]) -> Counter:
    return Counter(a)

def print_counts(c: Counter, lo: int, hi: int, title: str) -> None:
    print(f"\n{title}")
    print("value | count")
    for x in range(lo, hi + 1):
        print(f"{x:>5} | {c.get(x, 0):>5}")
    total = sum(c.values())
    uniq = len(c)
    print(f"total items={total}, unique values={uniq}")

def duplicates_info(a: List[int]) -> Tuple[int, int]:
    uniq = len(set(a))
    return uniq, len(a) - uniq

#Sorting, This part gave me the most trouble :( 

def insertion_sort_inplace(a: List[int]) -> None:
    for i in range(1, len(a)):
        key = a[i]
        j = i - 1
        while j >= 0 and a[j] > key:
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = key

def timed(action: Callable[[], None]) -> float:
    t0 = perf_counter()
    action()
    return perf_counter() - t0

def compare_sort_times(data: List[int], label: str) -> None:
    print(f"\n{label}")
# custom
    a = data[:]  
    t_custom = timed(lambda: insertion_sort_inplace(a))
    assert a == sorted(data)

# built-in
    b = data[:]
    t_builtin = timed(lambda: b.sort())

    print(f"custom sort: {t_custom:.6f} s")
    print(f"built in list.sort : {t_builtin:.6f} s")

def main() -> None:
# 1.
    x, loSmall, hiSmall = 100, 1, 16

    arr_random_small = fill_with_random(x, loSmall, hiSmall)
    arr_secrets_small = fill_with_secrets(x, loSmall, hiSmall)

    cnt_r_small = counts(arr_random_small)
    cnt_s_small = counts(arr_secrets_small)
    print("#1")
    print_counts(cnt_r_small, loSmall, hiSmall, "random module (1-16, x=100)")
    print_counts(cnt_s_small, loSmall, hiSmall, "secrets module (1-16, x=100)")
    """
    When running the code since it RNG, it didn't seem like there was any unifrom pattern
    but since i'm using the secert module it should be more secure and hopefully more random than RNG.
    """


# 2.
    loBig, hiBig = 1, 65535
    arr_random_big = fill_with_random(x, loBig, hiBig)
    arr_secrets_big = fill_with_secrets(x, loBig, hiBig)

    uniq_r, dups_r = duplicates_info(arr_random_big)
    uniq_s, dups_s = duplicates_info(arr_secrets_big)
    print("#2")
    print(f"\n1-65535 (x=100) — random: unique={uniq_r}, duplicates={dups_r}")
    print(f"1-65535 (x=100) — secrets: unique={uniq_s}, duplicates={dups_s}")
    """
    After increasing the range, i basically got no duplicates. Since reading all of sets was time consuming i looked up a way to 
    eaiser to display how many duplicates were created.
    """

# 3.
    data_random = fill_with_random(100, loSmall, hiSmall)
    compare_sort_times(data_random, "#3: 100 items, values 1-16")
    
# 4.
    data_big = fill_with_random(100, loBig, hiBig)
    compare_sort_times(data_big, "#4: 100 items, values 1-65535")
    """
    It appears that the custom sort was slightly faster but the built in sort 
    remained the same.
    """
# 5.
    data_500 = fill_with_random(500, loBig, hiBig)
    compare_sort_times(data_500, "#5: 500 items, values 1-65535")
    """
    the custom sort got significantly slower compared to its early times whereas the built in sort did a 
    much better job comapred to it's previous times.
    """


if __name__ == "__main__":
    main()
