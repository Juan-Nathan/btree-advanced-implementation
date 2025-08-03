import sys
import random

"""
B-Tree implementation with order statistics and range queries.
"""

# ───────────────────────────────────────────────────────────────────────────────
# B-Tree Node Implementation
# ───────────────────────────────────────────────────────────────────────────────

class BTreeNode:
    """
    A node in a B-Tree data structure.
    
    Each node contains:
    - keys: sorted list of keys stored in this node
    - children: list of child pointers (empty for leaf nodes)
    - subtree_size: total number of keys in the subtree rooted at this node
    - parent: pointer to parent node (None for root)
    """

    def __init__(self, min_degree, is_leaf=False, parent=None):
        """
        Initialize a new B-Tree node.
        
        Args:
            min_degree (int): Minimum degree of the B-Tree (t)
            is_leaf (bool): True if this is a leaf node
            parent (BTreeNode): Parent node reference (None for root)
        """
        self.keys = []                   # Sorted list of keys stored in this node
        self.children = []               # List of child node references  
        self.is_leaf = is_leaf           # True if leaf, False if internal node
        self.min_degree = min_degree     # Minimum degree (t)
        self.subtree_size = 0            # Total number of keys in subtree rooted here
        self.parent = parent             # Pointer to parent node (None for root)

    # ────────────────────── Size Management for Order Statistics ──────────────────────
    
    def recompute_subtree_size(self):
        """
        Recompute this node's subtree size from its children.
        
        For leaf nodes: size = number of keys in this node
        For internal nodes: size = number of keys in this node + sum of all children's sizes
        """
        if self.is_leaf:
            self.subtree_size = len(self.keys)
        else:
            # Sum up all keys in this node plus all keys in child subtrees
            self.subtree_size = len(self.keys) + sum(child.subtree_size for child in self.children)

    def update_ancestor_sizes(self, size_delta):
        """
        Propagate a size change up the tree to all ancestors.
        
        Args:
            size_delta (int): Change in size (+1 for insert, -1 for delete)
            
        This enables efficient order statistics by maintaining accurate
        subtree sizes without full recomputation.
        """
        current_node = self
        while current_node:
            current_node.subtree_size += size_delta
            current_node = current_node.parent

    # ───────────────────────── Node Splitting for Insertion ─────────────────────────
    
    def split_child(self, child_index, full_child):
        """
        Split a full child node and promote its middle key (median) to this node.
        
        Args:
            child_index (int): Index of the full child in self.children
            full_child (BTreeNode): The child node to split (must be full)
            
        This operation:
        1. Creates a new node containing the upper half of full_child's keys
        2. Promotes the middle key from full_child to this node
        3. Updates parent pointers and subtree sizes
        
        Used when inserting into a full child - we split it first to make room.
        """
        min_degree = self.min_degree
        
        # Create new node to hold upper half of the split child
        new_right_child = BTreeNode(min_degree, full_child.is_leaf, parent=self)

        # Split keys: middle key gets promoted, upper half goes to new node
        middle_key_index = min_degree - 1
        promoted_key = full_child.keys[middle_key_index]
        
        # Move upper half of keys to new node
        new_right_child.keys = full_child.keys[min_degree:]
        full_child.keys = full_child.keys[:middle_key_index]

        # If not a leaf, also split the children
        if not full_child.is_leaf:
            new_right_child.children = full_child.children[min_degree:]
            full_child.children = full_child.children[:min_degree]
            
            # Update parent pointers for moved children
            for child in new_right_child.children:
                child.parent = new_right_child

        # Recompute sizes for the split nodes
        full_child.recompute_subtree_size()
        new_right_child.recompute_subtree_size()

        # Insert the new child and promoted key into this node
        self.children.insert(child_index + 1, new_right_child)
        self.keys.insert(child_index, promoted_key)

        # Update this node's size (total keys in tree unchanged, just reorganized)
        self.recompute_subtree_size()

    def insert_non_full(self, key):
        """
        Insert a key into this node, assuming the node is not full.
        
        Args:
            key (int): The key to insert
            
        Recursively finds the correct position and inserts the key.
        Splits any full children encountered during the descent.
        """
        if self.is_leaf:
            # Simple insertion into sorted key list
            insort(self.keys, key)
            # Update size of this node and all ancestors
            self.update_ancestor_sizes(+1)
        else:
            # Find which child should contain this key
            child_index = bisect_left(self.keys, key)
            target_child = self.children[child_index]

            # If child is full, split it first
            if len(target_child.keys) == 2 * self.min_degree - 1:
                self.split_child(child_index, target_child)
                
                # After split, determine which of the two children gets the key
                if key > self.keys[child_index]:
                    child_index += 1
                    
            # Recursively insert into the appropriate child
            self.children[child_index].insert_non_full(key)

    # ──────────────────────── Node Merging and Borrowing for Deletion ──────────────────────────
    
    def merge_children(self, left_child_index):
        """
        Merge child at left_child_index with its right sibling.
        
        Args:
            left_child_index (int): Index of the left child to merge
            
        This operation:
        1. Pulls down the separating key from this node
        2. Combines left child, separator, and right child into one node
        3. Removes the right child and separator from this node
        
        Used during deletion when both siblings have minimum number of keys.
        """
        left_child = self.children[left_child_index]
        right_child = self.children[left_child_index + 1]

        # Pull separator key down from parent into left child
        separator_key = self.keys[left_child_index]
        left_child.keys.append(separator_key)
        
        # Move all keys from right child to left child
        left_child.keys.extend(right_child.keys)
        
        # If not leaves, also merge children
        if not left_child.is_leaf:
            left_child.children.extend(right_child.children)
            # Update parent pointers for moved children
            for child in right_child.children:
                child.parent = left_child

        # Remove separator key and right child from this node
        self.keys.pop(left_child_index)
        self.children.pop(left_child_index + 1)

        # Update sizes
        left_child.recompute_subtree_size()
        self.recompute_subtree_size()

    def borrow_from_left_sibling(self, child_index):
        """
        Borrow a key from the left sibling of child at child_index.
        
        Args:
            child_index (int): Index of child that needs more keys
            
        Moves one key from left sibling through parent to target child.
        Also moves rightmost child of left sibling if not leaves.
        """
        target_child = self.children[child_index]
        left_sibling = self.children[child_index - 1]

        # Rotate: left_sibling -> parent -> target_child
        target_child.keys.insert(0, self.keys[child_index - 1])
        self.keys[child_index - 1] = left_sibling.keys.pop()

        # If not leaves, also move a child pointer
        if not target_child.is_leaf:
            moved_child = left_sibling.children.pop()
            target_child.children.insert(0, moved_child)
            moved_child.parent = target_child

        # Update sizes (total unchanged, just redistributed)
        left_sibling.recompute_subtree_size()
        target_child.recompute_subtree_size()

    def borrow_from_right_sibling(self, child_index):
        """
        Borrow a key from the right sibling of child at child_index.
        
        Args:
            child_index (int): Index of child that needs more keys
            
        Moves one key from right sibling through parent to target child.
        Also moves leftmost child of right sibling if not leaves.
        """
        target_child = self.children[child_index]
        right_sibling = self.children[child_index + 1]

        # Rotate: target_child <- parent <- right_sibling
        target_child.keys.append(self.keys[child_index])
        self.keys[child_index] = right_sibling.keys.pop(0)

        # If not leaves, also move a child pointer
        if not target_child.is_leaf:
            moved_child = right_sibling.children.pop(0)
            target_child.children.append(moved_child)
            moved_child.parent = target_child

        # Update sizes (total unchanged, just redistributed)
        right_sibling.recompute_subtree_size()
        target_child.recompute_subtree_size()

    def ensure_child_has_enough_keys(self, child_index):
        """
        Ensure child at child_index has at least min_degree keys before descending.
        
        Args:
            child_index (int): Index of child to check
            
        If child has fewer than min_degree keys, either:
        1. Borrow from a sibling with extra keys, or
        2. Merge with a sibling if both have minimum keys
        
        This maintains B-Tree invariants during deletion.
        """
        min_keys_required = self.min_degree
        
        # Try borrowing from left sibling first
        if (child_index > 0 and 
            len(self.children[child_index - 1].keys) >= min_keys_required):
            self.borrow_from_left_sibling(child_index)
            
        # Try borrowing from right sibling
        elif (child_index < len(self.children) - 1 and 
              len(self.children[child_index + 1].keys) >= min_keys_required):
            self.borrow_from_right_sibling(child_index)
            
        # Must merge - merge with right or left sibling
        else:
            if child_index < len(self.children) - 1:
                # Merge with right sibling
                self.merge_children(child_index)
            else:
                # Merge with left sibling
                self.merge_children(child_index - 1)

# ───────────────────────────── Main B-Tree Class ─────────────────────────────

class BTree:
    """
    B-Tree data structure supporting order statistics and range queries.
    
    A B-Tree is a self-balancing tree data structure that maintains sorted data
    and allows searches, insertions, and deletions in logarithmic time.
    
    This implementation adds:
    - Order statistics: select(k) finds k-th smallest element, rank(x) finds position of x
    - Range queries: 
        - Find all keys in a given range
        - Find all prime numbers in a range
    
    Properties:
    - All keys in the tree are distinct
    - Tree remains balanced, with a height O(log n), where n is total number of keys in the tree
    - Leaf nodes contain only keys (no children)
    - Internal nodes have len(keys) + 1 pointers to children
    - All keys in child[i] < keys[i] < all keys in child[i+1] (distinct keys)
    - Each node has at most 2t - 1 keys
    - Each non-root node has at least t - 1 keys
    """
    
    def __init__(self, min_degree):
        """
        Initialize an empty B-Tree.
        
        Args:
            min_degree (int): Minimum degree (t), must be >= 2
                            - Nodes can have 2t - 1 keys maximum
                            - Non-root nodes must have t - 1 keys minimum
        """
        if min_degree < 2:
            raise ValueError("Minimum degree must be >= 2")
        self.min_degree = min_degree
        self.root = BTreeNode(min_degree, is_leaf=True)

    # ───────────────────────────── Search ────────────────────────────────
    
    def _search_in_subtree(self, node, key):
        """
        Search for a key in the subtree rooted at node.
        
        Args:
            node (BTreeNode): Root of subtree to search
            key (int): Key to find
            
        Returns:
            bool: True if key exists, False otherwise
        """
        # Binary search within this node's keys
        key_index = bisect_left(node.keys, key)
        
        # Check if we found an exact match
        if key_index < len(node.keys) and node.keys[key_index] == key:
            return True
            
        # If leaf node and no match, key doesn't exist
        if node.is_leaf:
            return False
            
        # Recursively search appropriate child subtree
        return self._search_in_subtree(node.children[key_index], key)

    def search(self, key):
        """
        Search for a key in the B-Tree.
        
        Args:
            key (int): Key to search for
            
        Returns:
            bool: True if key exists in tree, False otherwise
        """
        return self._search_in_subtree(self.root, key)

    # ───────────────────────────── Insertion ────────────────────────────────
    
    def insert(self, key):
        """
        Insert a key into the B-Tree.
        
        Args:
            key (int): Key to insert (must be positive integer)
            
        Ignores duplicate keys. Maintains B-Tree properties by splitting
        full nodes as needed during insertion.
        """
        if key <= 0:
            raise ValueError("Keys must be positive integers")
            
        # Don't insert duplicates
        if self.search(key):
            return
            
        root = self.root
        
        # If root is full, create new root and split old root
        if len(root.keys) == 2 * self.min_degree - 1:
            new_root = BTreeNode(self.min_degree, is_leaf=False)
            new_root.children.append(root)
            root.parent = new_root
            new_root.split_child(0, root)
            self.root = new_root
            
        # Insert into the (possibly new) root
        self.root.insert_non_full(key)

    # ───────────────────────────── Deletion ────────────────────────────────
    
    def _find_minimum_key(self, node):
        """
        Find the minimum key in subtree rooted at node.
        """
        while not node.is_leaf:
            node = node.children[0]
        return node.keys[0]

    def _find_maximum_key(self, node):
        """
        Find the maximum key in subtree rooted at node.
        """
        while not node.is_leaf:
            node = node.children[-1]
        return node.keys[-1]

    def _remove_from_leaf(self, node, key_index):
        """
        Remove key at key_index from leaf node.
        """
        node.keys.pop(key_index)
        node.update_ancestor_sizes(-1)

    def _remove_from_internal_node(self, node, key_index):
        """
        Remove key at key_index from internal node.
        
        Uses one of three strategies:
        1. Replace with predecessor if left child has enough keys
        2. Replace with successor if right child has enough keys  
        3. Merge children and recurse if both children have minimum keys
        """
        key_to_remove = node.keys[key_index]
        left_child = node.children[key_index]
        right_child = node.children[key_index + 1]
        
        # Replace with predecessor
        if len(left_child.keys) >= self.min_degree:
            predecessor = self._find_maximum_key(left_child)
            node.keys[key_index] = predecessor
            self._delete_from_subtree(left_child, predecessor)
            
        # Replace with successor
        elif len(right_child.keys) >= self.min_degree:
            successor = self._find_minimum_key(right_child)
            node.keys[key_index] = successor
            self._delete_from_subtree(right_child, successor)
            
        # Merge and recurse
        else:
            node.merge_children(key_index)
            self._delete_from_subtree(node.children[key_index], key_to_remove)

    def _delete_from_subtree(self, node, key):
        """
        Delete key from subtree rooted at node.
        
        Handles all cases of B-Tree deletion while maintaining invariants.
        """
        key_index = bisect_left(node.keys, key)
        
        # Key is in this node
        if key_index < len(node.keys) and node.keys[key_index] == key:
            if node.is_leaf:
                self._remove_from_leaf(node, key_index)
            else:
                self._remove_from_internal_node(node, key_index)
                
        # Key is in subtree
        else:
            if node.is_leaf:
                return  # Key not found
                
            # Ensure target child has enough keys before descending
            if len(node.children[key_index].keys) < self.min_degree:
                node.ensure_child_has_enough_keys(key_index)
                
                # After merge/borrow, target child might have moved
                if key_index >= len(node.keys) + 1:
                    # Merged with left sibling - key is now in left child
                    self._delete_from_subtree(node.children[key_index - 1], key)
                else:
                    # Merged with right sibling or borrowed - position unchanged
                    self._delete_from_subtree(node.children[key_index], key)
            else:
                # Child has enough keys - safe to descend directly
                self._delete_from_subtree(node.children[key_index], key)

    def delete(self, key):
        """
        Delete a key from the B-Tree.
        
        Args:
            key (int): Key to delete
            
        Ignores requests to delete non-existent keys.
        Maintains B-Tree properties during deletion.
        """
        # Key not found, nothing to delete
        if not self.search(key):
            return
            
        self._delete_from_subtree(self.root, key)
        
        # If root becomes empty after deletion, make its only child the new root
        if not self.root.is_leaf and len(self.root.keys) == 0:
            self.root = self.root.children[0]
            self.root.parent = None

    # ────────────────────────── Order Statistics ──────────────────────────────
    
    def _select_kth_smallest(self, node, k):
        """
        Find the k-th smallest key in subtree rooted at node.
        
        Args:
            node (BTreeNode): Root of subtree
            k (int): 1-based rank to find
            
        Returns:
            int: The k-th smallest key, or -1 if k is out of bounds
        """
        key_index = 0
        
        while key_index < len(node.keys):
            # Count keys in left subtree
            left_subtree_size = 0 if node.is_leaf else node.children[key_index].subtree_size
            
            # If k-th element is in left subtree
            if k <= left_subtree_size:
                return self._select_kth_smallest(node.children[key_index], k)
                
            # Account for left subtree
            k -= left_subtree_size
            
            # If k-th element is this key
            if k == 1:
                return node.keys[key_index]
                
            # Account for this key  
            k -= 1
            key_index += 1

        # k-th element must be in rightmost subtree
        if node.is_leaf:
            return -1
        return self._select_kth_smallest(node.children[-1], k)

    def select(self, k):
        """
        Find the k-th smallest key in the tree (1-based indexing).
        
        Args:
            k (int): Rank to find (1 = smallest, 2 = second smallest, etc.)
            
        Returns:
            int: The k-th smallest key, or -1 if k is out of bounds
        """
        if k < 1 or k > self.root.subtree_size:
            return -1
        return self._select_kth_smallest(self.root, k)

    def _find_rank(self, node, key):
        """
        Find the rank (1-based position) of key in subtree rooted at node.
        
        Args:
            node (BTreeNode): Root of subtree
            key (int): Key to find rank of
            
        Returns:
            int: 1-based rank of key, or -1 if key not found
        """
        key_index = 0
        rank_so_far = 0

        while key_index < len(node.keys):
            left_subtree_size = 0 if node.is_leaf else node.children[key_index].subtree_size

            # Key is smaller than current key - must be in left subtree (if it exists)
            if key < node.keys[key_index]:
                if node.is_leaf:
                    return -1  # Key not found
                subtree_rank = self._find_rank(node.children[key_index], key)
                return -1 if subtree_rank == -1 else rank_so_far + subtree_rank

            # Found exact match
            if key == node.keys[key_index]:
                return rank_so_far + left_subtree_size + 1

            # Key is larger - skip this key and its left subtree
            rank_so_far += left_subtree_size + 1
            key_index += 1

        # Key must be in rightmost subtree (if it exists)
        if node.is_leaf:
            return -1  # Key not found
            
        subtree_rank = self._find_rank(node.children[-1], key)
        return -1 if subtree_rank == -1 else rank_so_far + subtree_rank

    def rank(self, key):
        """
        Find the rank (1-based position) of a key in sorted order.
        
        Args:
            key (int): Key to find rank of
            
        Returns:
            int: 1-based rank of key (1 = smallest), or -1 if key not found
        """
        return self._find_rank(self.root, key)

    # ───────────────────────────── Range Queries ──────────────────────────────
    
    def _collect_keys_in_range(self, node, min_key, max_key, result_list):
        """
        Collect all keys in range [min_key, max_key] from subtree rooted at node.
        
        Args:
            node (BTreeNode): Root of subtree to search
            min_key (int): Minimum key to include (inclusive)
            max_key (int): Maximum key to include (inclusive)
            result_list (List[int]): List to append found keys to
            
        Uses efficient tree traversal - only visits subtrees that might contain keys in range.
        """
        # Find first key >= min_key
        start_index = bisect_left(node.keys, min_key)

        # Check left subtree of first relevant key
        if not node.is_leaf:
            self._collect_keys_in_range(node.children[start_index], min_key, max_key, result_list)

        # Collect all keys in range from this node
        key_index = start_index
        while key_index < len(node.keys) and node.keys[key_index] <= max_key:
            result_list.append(node.keys[key_index])
            
            # Also check right subtree of this key
            if not node.is_leaf:
                self._collect_keys_in_range(node.children[key_index + 1], min_key, max_key, result_list)
                
            key_index += 1

    def keys_in_range(self, min_key, max_key):
        """
        Find all keys in the range [min_key, max_key] (inclusive).
        
        Args:
            min_key (int): Minimum key to include
            max_key (int): Maximum key to include
            
        Returns:
            List[int]: Sorted list of keys in range, or [-1] if no keys found
        """
        if min_key > max_key:
            min_key, max_key = max_key, min_key
            
        result = []
        self._collect_keys_in_range(self.root, min_key, max_key, result)
        return result if result else [-1]
    
    def primes_in_range(self, min_key, max_key):
        """
        Find all prime numbers in the range [min_key, max_key].
        
        Args:
            min_key (int): Minimum key to include
            max_key (int): Maximum key to include
            
        Returns:
            List[int]: Sorted list of prime numbers in range, or [-1] if none found
        """
        keys_in_range = self.keys_in_range(min_key, max_key)
        if keys_in_range == [-1]:
            return [-1]
            
        prime_numbers = [key for key in keys_in_range if is_prime(key)]
        return prime_numbers if prime_numbers else [-1]
    
# ───────────────────────────── Helper Functions ──────────────────────────────

def bisect_left(sorted_list, target_value):
    """
    Return the leftmost index at which target_value should be inserted in sorted_list.
    
    Uses binary search to find the insertion point that maintains sorted order.
    If target_value already exists in the list, returns the index of the first occurrence.
    
    Args:
        sorted_list (List[int]): Sorted list to search in
        target_value (int): Value to find insertion point for
        
    Returns:
        int: Index where target_value should be inserted (0 to len(sorted_list))
    """
    left_bound, right_bound = 0, len(sorted_list)
    
    while left_bound < right_bound:
        middle_index = (left_bound + right_bound) // 2
        
        if sorted_list[middle_index] < target_value:
            left_bound = middle_index + 1        
        else:                                         
            right_bound = middle_index                   
            
    return left_bound

def insort(sorted_list, new_value):
    """
    Insert new_value into sorted_list in place, maintaining sorted order.
    
    Finds the correct insertion position using binary search, then inserts
    the value at that position. The list is modified in-place.
    
    Args:
        sorted_list (List[int]): Sorted list to insert into (modified in-place)
        new_value (int): Value to insert
    """
    insertion_index = bisect_left(sorted_list, new_value)
    sorted_list.insert(insertion_index, new_value)

def is_prime(n, k = 40):
    """
    Miller-Rabin primality test (probabilistic).
    
    Tests whether n is likely prime using k random witnesses.
    
    Args:
        n: Integer to test
        k: Number of witness rounds (default 40 gives error probability ≤ 1/4^40, which is practically negligible)
    
    Returns:
        True if n is probably prime, False if definitely composite
    """
    # Handle small cases
    if n == 2 or n == 3:
        return True
    if n < 2 or n % 2 == 0:
        return False
    
    # Express n-1 as 2^s × t where t is odd
    s = 0
    t = n - 1
    while t % 2 == 0:
        s += 1
        t //= 2
    
    # Test k random witnesses
    for _ in range(k):
        # Pick random witness a ∈ [2, n-2]
        a = random.randint(2, n - 2)
        
        # Compute a^t mod n
        x = pow(a, t, n)
        
        # Check if a^t ≡ 1 or -1 (mod n)
        if x == 1 or x == n - 1:
            continue  # This witness passes
        
        # Square x repeatedly (s-1 times), looking for -1
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            # If we never found -1, n is composite
            return False
    
    # All witnesses passed
    return True

# ────────────────────────────────── Command Line Interface ────────────────────────────────────

def read_integers_from_file(file_path):
    """
    Read integers from a text file, one per line.
    
    Args:
        file_path (str): Path to file containing integers
        
    Yields:
        int: Each integer found in the file
    """
    with open(file_path) as file:
        for line in file:
            line = line.strip()
            if line:  # Skip empty lines
                yield int(line)

def main():
    """
    Main function to run B-Tree operations from command line.
    
    Expected usage:
        python script.py <min_degree> <insert_file> <delete_file> <commands_file>
    """
    args = sys.argv[1:]
    
    if len(args) != 4:
        sys.exit("Usage: python btree.py <min_degree> <insert_file> <delete_file> <commands_file>")

    # Parse minimum degree parameter 
    try:
        min_degree = int(args[0])
        if min_degree < 2:
            raise ValueError
    except ValueError:
        sys.exit("min_degree must be an integer >= 2")

    # Extract file paths
    insert_file, delete_file, commands_file = args[1:]

    # Build B-Tree with specified minimum degree
    btree = BTree(min_degree)

    # Insert all valid keys from insert file
    for key in read_integers_from_file(insert_file):
        if key <= 0:
            print(f"Skipped invalid key (non-positive): {key}")
            continue
        btree.insert(key)
            
    # Delete all keys from delete file
    for key in read_integers_from_file(delete_file):
        btree.delete(key)

    # Process commands and collect results
    results = []
    
    # Read commands file line by line
    try:
        with open(commands_file) as cmd_file:
            for line in cmd_file:
                line = line.strip()
                if not line: # Skip empty lines
                    continue

                # Split into command and arguments
                command_parts = line.split()
                
                try:
                    # Extract command name
                    command = command_parts[0]
                    
                    if command == "select":
                        k = int(command_parts[1])
                        result = btree.select(k)
                        results.append(str(result))
                        
                    elif command == "rank":
                        key = int(command_parts[1])
                        result = btree.rank(key)
                        results.append(str(result))
                        
                    elif command == "keysInRange":
                        min_key, max_key = map(int, command_parts[1:3])
                        result = btree.keys_in_range(min_key, max_key)
                        if result == [-1]:
                            results.append("-1")
                        else:
                            results.append(" ".join(map(str, result)))
                            
                    elif command == "primesInRange":
                        min_key, max_key = map(int, command_parts[1:3])
                        result = btree.primes_in_range(min_key, max_key)
                        if result == [-1]:
                            results.append("-1")
                        else:
                            results.append(" ".join(map(str, result)))
                            
                except Exception:
                    # Handle malformed commands gracefully
                    results.append("-1")
                
    except Exception as e:
        sys.exit(f"Error reading commands file: {e}")

    # Write results to output file
    try:
        with open("output.txt", "w") as out_file:
            for line in results:
                out_file.write(f"{line}\n")
    except Exception as e:
        sys.exit(f"Error writing output file: {e}")

if __name__ == "__main__":
    main()