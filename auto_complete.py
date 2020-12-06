import requests
import time


class Node:

    def __init__(self, val=""):
        self.val = val  # Node's letter value
        self.previous = None  # Node(a)
        self.next = {}  # {"d": Node(b)}
        # self.passes = 0
        self.end = False

    def add_next(self, next_node):
        copy = self.next.copy()
        copy.update({next_node.val: next_node})
        self.next = copy.copy()

    def add_previous(self, prev_node):
        self.previous = prev_node

    def __repr__(self):
        return self.val


def get_words():
    word_site = "https://www.mit.edu/~ecprice/wordlist.10000"
    response = requests.get(word_site)
    words = response.content.splitlines()
    words = [word.decode() for word in words]
    return words


# Class to which you pass a list of words, and then you can use a method to take in a string and return suggestions


class AutoComplete:
    suggestions = []

    def __init__(self, words=None):
        self.nul_node = Node()
        if not words:
            return
        self.load(words=words)
        for word in words:
            # Build the Trie
            self.trie_gen(word, self.nul_node)

    def load(self, words=(), default=False):
        self.nul_node = Node()
        if default:
            words = get_words()
        for word in words:
            # Build the Trie
            self.trie_gen(word, self.nul_node)

    def trie_gen(self, word, node):
        # Recursive function which updates the Trie with a new word by passing in
        # that word with the nul node
        if not word:
            # Mark an end node
            node.end = True
            return
        try:
            next_node = node.next[word[0]]
        except KeyError:
            next_node = Node(word[0])
            node.add_next(next_node)
            next_node.add_previous(node)
        finally:
            word = word[1:]
            return self.trie_gen(word, next_node)

    def word_gen(self, node, NUM_SUGG):
        if node.end:
            self.suggestions.append(self.get_word(node))
            if len(self.suggestions) == NUM_SUGG:
                raise Exception("Done!")

        for letter, node_ in node.next.items():
            self.word_gen(node_, NUM_SUGG)

    def get_node(self, string, node):
        if not string:
            return node
        char = string[0]
        string = string[1:]
        try:
            return self.get_node(string, node.next[char])
        except KeyError:
            # In case the input doesn't match any name, return []
            return []

    @staticmethod
    def get_word(end_node):
        word = ""
        while True:
            word += end_node.val
            end_node = end_node.previous
            if not end_node:
                return word[::-1]

    def auto(self, input_, max_sugg=5):
        self.suggestions = []
        node = self.get_node(input_, self.nul_node)
        try:
            self.word_gen(node, max_sugg)
        except Exception as e:
            if e == "Done!":
                pass
        return self.suggestions
