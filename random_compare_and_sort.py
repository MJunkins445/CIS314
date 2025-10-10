import random
import secrets
import time
from collections import Counter
from copy import deepcopy

def random_count(n=100, lo=1, hi=16):
    row = [random.randint(lo, hi) for _ in range(n)]
    return Counter(row)

def secret_count(n=100, lo=1, hi=16):
    row = [secrets.randbelow(hi - lo + 1) + lo for _ in range(n)]
    return Counter(row)

def compare_counts(cnt1, cnt2, lo=1, hi=16):
    print("Value | random count | secrets count")
    for x in range(lo, hi + 1):
        print(f"{x:5d} | {cnt1.get(x, 0):12d} | {cnt2.get(x, 0):13d}")

def uniqueness_report(cnt, label):
    total = sum(cnt.values())
    uniques = len(cnt)
    print(f"{label}: {uniques} unique out of {total} draws")
    if uniques < total:
        print(f"{total - uniques} duplicate(s) found")
    else:
        print("No duplicates")

def make_list(n=100, lo=1, hi=16, use_secrets=True):
    
    if use_secrets:
        return [secrets.randbelow(hi - lo + 1) + lo for _ in range(n)]
    return [random.randint(lo, hi) for _ in range(n)]

def insertion_sort(a):
    for i in range(1, len(a)):
        key = a[i]
        j = i - 1
        while j >= 0 and a[j] > key:
            a[j] = a[j - 1]
            j -= 1
        a[j + 1] = key
    return a

def time_call(fn, *args, **kwargs):
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    t1 = time.perf_counter()
    return result, (t1 - t0)

def benchmark_sorts(data):
    """Time your own sort vs. the built-in .sort() on the same data."""
    a_custom = deepcopy(data)
    a_builtin = deepcopy(data)

    _, t_custom = time_call(insertion_sort, a_custom)

    def builtin_sort(lst):
        lst.sort()
        return lst
    _, t_builtin = time_call(builtin_sort, a_builtin)

    print("\n--- Sorting benchmark on 100 elements in [1,16] ---")
    print(f"Custom insertion_sort: {t_custom*1e6:,.0f} µs")
    print(f"Built-in list.sort():  {t_builtin*1e6:,.0f} µs")
    print("Lists equal after sort? ", a_custom == a_builtin)

def main():
    print("Small range test (1–16)")
    cnt_r = random_count()
    cnt_s = secret_count()
    compare_counts(cnt_r, cnt_s)

    print("\nLarge range test (1–65535)")
    cnt_r_big = random_count(16, 1, 65535)
    cnt_s_big = secret_count(16, 1, 65535)
    uniqueness_report(cnt_r_big, "random")
    uniqueness_report(cnt_s_big, "secrets")

    data = make_list(n=100, lo=1, hi=16, use_secrets=True)
    print("Sample of the unsorted list (first 20):", data[:20])
    benchmark_sorts(data)

if __name__ == "__main__":
    main()

'''
#1. 
when running the code since it RNG, it didn't seem like there was any unifrom pattern
but since i'm using the secert module it should be more secure and hopefully more random than RNG.

#2
After increasing the range, i basically got no duplicates. Since reading all of sets was time consuming i looked up a way to 
eaiser to display how many duplicates were created I found the unqueness report on github which worked well.

#3

'''
