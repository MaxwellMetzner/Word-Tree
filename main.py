import sys
import os
import pickle
import time

#TODO Make an analysis of the letters in the tree to determine the best letters to use and incorporate into score
#TODO the wordle guesses need to alter the tree and remove nodes that are not possible to assist in score

#TODO have a mode where it makes the best guess while not attempting to solve?

#TODO make a wordscapes generator that fills up an X by Y grid with random words using a set number of letters, trying to pack densely as possible using a select number of letters

#TODO create a computer vision script that can take a screenshot of the wordle game and return the letters and colors so the game may be played automatically

#region Objects

class Node:
    def __init__(self, char, level=-1, freq=0, is_end_of_word=False, parent=None, children=None):
        self.char = char
        self.level = level
        self.freq = freq
        self.is_end_of_word = is_end_of_word
        self.parent = parent
        self.children = children if children is not None else []  # Initialize a new list if None

    def __str__(self):
        word = self.char
        node = self
        while node.parent and node.level > 0:
            node = node.parent
            word = node.char + word
        return word
    
    def score(self):
        score = 0
        node = self
        while node:
            score += node.freq
            node = node.parent
        return score
    
    def add(self, char, level):
        child = Node(char, level)
        self.children.append(child)
        child.parent = self
        return child

    def remove(self):
        self.is_end_of_word = False
        node = self
        while node:
            # A nonnegative frequency indicates another word is using this node
            node.freq -= 1
            if node.freq < 1:
                if node.parent:
                    node.parent.children.remove(node)
            node = node.parent

    def print_tree(self):
        def print_tree_helper(node):
            print(f"{'  ' * node.level}{node.char},l:{node.level},f:{node.freq},{node.is_end_of_word}")
            for child in node.children:
                print_tree_helper(child)
        print_tree_helper(self)


#endregion

#region CRUD operations
def save_tree(root, file_path):
    with open(file_path, "wb") as file:
        pickle.dump(root, file)

def load_tree(file_path):
    with open(file_path, "rb") as file:
        root = pickle.load(file)
    return root

def process_txt_file(file_path):
    start_time = time.time()
    print("Processing Dictionary File")
    with open(file_path, "r") as file:
        lines = file.readlines()

    lines = [line.lower().replace("\n", "").replace(" ", "").replace("\t", "").replace("\r", "").replace("\x0c", "") for line in lines]
    lines = ["".join(filter(str.isalpha, line)) for line in lines]

    root = Node("", freq=0)

    # Add each word to the tree by iterating through each character in the word and adding nodes as needed
    for line in lines:
        node = root
        for i in range(len(line)):
            node.freq += 1
            char = line[i]
            found = False
            for child in node.children:
                if child.char == char:
                    node = child
                    found = True
                    break
            if not found:
                new_node = node.add(char, i)
                node = new_node
        node.is_end_of_word = True
        node.freq += 1

    print("Dictionary File Processed in ", round(time.time() - start_time, 2), " seconds")
    print("Saving Tree")
    savelocation = file_path + ".pkl"
    save_tree(root, savelocation)
    print("Tree saved to: ", savelocation, " in ", round(time.time() - start_time, 2), " seconds")
    return root

#endregion

#region Search

def search(root, word, repeating):
    # Generates all possible words that can be formed by using the letters of the input word with or without repeating any letter in any combination.
    # Returns a list of all valid words that meet the criteria.
    # TODO returning single letters as words
    word = word.lower()
    output = []
    def search_helper(node, word, output):
        if node.is_end_of_word:
            output.append(node)
        for child in node.children:
            if child.char in word:
                search_helper(child, word if repeating else word.replace(child.char, "", 1), output)

    search_helper(root, word, output)

    # sort by level descending
    output = sorted(output, key=lambda x: x.level, reverse=True)

    return output

#endregion

#region Wordle

def wordle_prep(root):
    # Only interested in 5 character words
    def trim(node):
        if node.is_end_of_word and node.level != 4:
            node.remove()
        children = node.children.copy()
        for child in children:
            trim(child)

    trim(root)

    return root

def wordle_search(root, new_word, rules=[]):
    # Takes a single string "new_word" as input.
    # Rules contains 5 alphabets representing allowed letters for each position in the word.
    # The function should return a list of all valid words that can be formed using the rules and the new_word and their score, sorted in descending order of score.

    # TODO how to deal with a letter being yellow then gray

    if not rules:
        rules = ["abcdefghijklmnopqrstuvwxyz"] * 5

    parsed = []
    i = 0
    while i < len(new_word):
        if i < len(new_word) - 1 and (new_word[i] == '.' or new_word[i] == ' '):
            parsed.append(new_word[i:i+2])
            i += 2
        else:
            parsed.append(new_word[i])
            i += 1

    # For each element in parsed, update the rules
    # Capital letters represent the correct letter in the correct position.
    # Lowercase letters represent the correct letter in the wrong position.
    # A period then a character represents a letter that is not in the word.

    for i in range(len(parsed)):
        if parsed[i].isupper():
            rules[i] = parsed[i].lower()
        elif parsed[i][0] == '.':
            for j in range(5):
                if len(rules[j]) > 1:
                    rules[j] = rules[j].replace(parsed[i][1], "")
        else:
            rules[i] = rules[i].replace(parsed[i], "")
            # If the letter is not in the root, add it
            if parsed[i] not in root.char:
                # if there is a rule with a single letter equal to the parsed letter, add an extra letter to the root
                if any([len(rule) == 1 and rule == parsed[i] for rule in rules]):
                    root.char += parsed[i]
                root.char += parsed[i]
            
            # if there are only two possible positions for a letter, remove the other possibilities
            if len([rule for rule in rules if len(rule) > 1]) == 2:
                for j in range(5):
                    if len(rules[j]) > 1 and parsed[i] in rules[j]:
                        rules[j] = parsed[i]

    
    # Search for words with each letter must be in the rules for that position
    # For example, for the word "apple", rules[0] must contain "a", rules[1] must contain "p", etc.    
    def search_helper(node, rules, level, output):
        if node.is_end_of_word:
            output.append(node)
        for child in node.children:
            if child.char in rules[level]:
                search_helper(child, rules, level + 1, output)

    output = []
    search_helper(root, rules, 0, output)

    def filter_words(word_list, match):
        def contains_all_letters(word, letters):
            for letter in letters:
                if letter not in word:
                    return False
            return True
        return [word for word in word_list if contains_all_letters(str(word), match)]

    output = filter_words(output, root.char)
    
    output = sorted(output, key=lambda x: x.score(), reverse=True)
    
    # Print the top 5 words
    print("Top 5 Words: ")
    for word in output[:5]:
        print(str(word), " Score: ", word.score())
    
    return rules

#endregion

#region CLI

def main():
    file_path = None

    # Search the local directory for a .pkl file, if found ask the user if they want to use it
    print("Searching for a tree file (.pkl) in the local directory")
    for file in os.listdir(os.path.dirname(sys.argv[0])):
        if file.endswith(".pkl"):
            print("Found: ", file)
            print("Use this file? (y/n)")
            if input().lower() == "y":
                file_path = os.path.join(os.path.dirname(sys.argv[0]), file)
                break

    # If no .pkl file is found, search for a .txt file
    if not file_path:
        print("Searching for a dictionary file (.txt) in the local directory")
        for file in os.listdir(os.path.dirname(sys.argv[0])):
            if file.endswith(".txt"):
                print("Found: ", file)
                print("Use this file? (y/n)")
                if input().lower() == "y":
                    file_path = os.path.join(os.path.dirname(sys.argv[0]), file)
                    break

    # If no .pkl or .txt file is found, ask for a file path
    if not file_path:
        print("No dictionary file (.txt) or tree file (.pkl) found in the local directory")
        print("Please provide a file path to a dictionary file (.txt) or a tree file (.pkl)")
        file_path = input()

        # Fix the file path if it uses backslashes or quotes
        file_path = file_path.replace("\\", "/").replace("\"", "")

        if not os.path.exists(file_path):
            print("File not found")
            sys.exit()

    # If the file is a .txt file, process it and save the tree
    if file_path.endswith(".txt"):
        root = process_txt_file(file_path)

    # If the file is a .pkl file, load the tree
    elif file_path.endswith(".pkl"):
        root = load_tree(file_path)

    # If the file is not a .txt or .pkl file, exit
    else:
        print(f"Warning: {file_path} is not a .txt or .pkl file")

    # Ask the user if they want to play in wordle mode or standard mode
    print("Would you like to play in wordle mode? (y/n)")
    wordle_mode = input().lower() == "y"

    if wordle_mode:          
        
        # make a copy of the root so that the original root is not modified
        new_root = wordle_prep(root)
        rules = []
        allowed_chars = ""

        while True:
            rules = wordle_search(new_root, allowed_chars, rules)   

            print("Please provide a list of allowed characters. Press enter to restart or Ctrl+C to exit")
            allowed_chars = input()

            if not allowed_chars:
                new_root.char = ""  
                rules = []
                allowed_chars = "" 
                print("Restarting...")
                continue

    # Ask the user if letters can be repeated
    print("Can letters be repeated? (y/n)")
    repeating = input().lower() == "y"

    while True:
        # Take user input for allowed characters
        print("Please provide a list of allowed characters. Press enter to exit")
        allowed_chars = input()

        # Exit if the user presses enter
        if not allowed_chars:
            break

        # Search for words using the allowed characters
        words = search(root, allowed_chars, repeating)
        print("Words found: ")
        for word in words:
            print(str(word))

if __name__ == "__main__":
    main()

#endregion