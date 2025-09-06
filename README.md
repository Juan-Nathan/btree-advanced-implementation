# 🌳 Advanced B-Tree with Order Statistics and Range Queries

This project implements a powerful and feature-rich **B-Tree** data structure in Python, extending the canonical CLRS version with advanced functionality such as:

- Order statistics
- Range queries
- Functional command-line interface (CLI)

The implementation maintains **subtree sizes** to support **efficient statistical operations** and uses a **traversal-optimized structure** to enable **fast range searches**.

## Features

- **Insert/Delete/Search** in logarithmic time (`O(log n)`)
- **Order Statistics**:
  - `select(k)` returns the `k`-th smallest element
  - `rank(x)` returns the 1-based position of key `x`
- **Range Queries**:
  - `keys_in_range(min, max)` returns all keys between `min` and `max`
  - `primes_in_range(min, max)` finds all prime numbers in that range using the **Miller-Rabin** primality test
- Built-in CLI support for scripted input/output using text files

## Input Constraints

- All keys must be positive integers (≥ 1).
- Keys must be distinct—duplicates are automatically ignored.

## B-Tree Properties

In a B-Tree with minimum degree `t`:

- Each node contains at most `2t - 1` keys.
- Each non-root node contains at least `t - 1` keys.
- An internal node with `k` keys has exactly `k + 1` children.
- All leaf nodes appear at the same level (balanced) and have no children.
- The height of the tree is `O(log n)`, where `n` is the total number of keys.

## How to Run

You can run the B-Tree program directly from the command line using:
`python btree.py t keystoinsert.txt keystodelete.txt commands.txt`

Where:
- `t` is the minimum degree of the B-Tree (must be an integer ≥ 2)
- `keystoinsert.txt` contains positive integers to insert (one per line)
- `keystodelete.txt` contains keys to delete (one per line)
- `commands.txt` contains commands to query the tree (see below)

## Output

Results are written to a file named:
`output.txt`

Each line corresponds to one command from `commands.txt`.

## Author

Developed by Juan Nathan.












