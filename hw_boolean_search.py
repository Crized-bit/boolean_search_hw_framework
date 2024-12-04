#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import codecs


class BooleanNode:
    """
    Узел дерева для представления булевых операций.
    """

    def __init__(self, value, left=None, right=None):
        self.value = value  # Значение узла (операция или термин)
        self.left = left  # Левое поддерево
        self.right = right  # Правое поддерево


def parse_query(query):
    """
    Построение дерева из булевого запроса.
    Поддерживаются операции &, |, !, скобки и термины.
    :param query: Булев запрос в виде строки.
    :return: Корневой узел дерева.
    """

    def tokenize(query):
        """Разделение запроса на токены."""
        tokens = []
        token = ''
        for char in query:
            if char in '() |!':
                if token:
                    tokens.append(token)
                    token = ''
                tokens.append(char)
            else:
                token += char
        if token:
            tokens.append(token)
        return tokens

    def parse(tokens):
        """Рекурсивный парсер для построения дерева."""
        stack = []  # Для операндов и поддеревьев
        operators = []  # Для операторов

        def apply_operator():
            operator = operators.pop()
            if operator == '!':
                operand = stack.pop()
                stack.append(BooleanNode(operator, left=operand))
            else:
                right = stack.pop()
                left = stack.pop()
                stack.append(BooleanNode(operator, left=left, right=right))

        precedence = {'!': 3, ' ': 2, '|': 1}

        for token in tokens:
            if token.isalnum() or "_" in token:  # Операнд
                stack.append(BooleanNode(token))
            elif token == '(':
                operators.append(token)
            elif token == ')':
                while operators and operators[-1] != '(':
                    apply_operator()
                operators.pop()  # Убираем '(' !
            else:  # Оператор
                while (operators and operators[-1] != '(' and
                       precedence[operators[-1]] >= precedence[token]):
                    apply_operator()
                operators.append(token)

        while operators:
            apply_operator()

        return stack[0]  # Корень дерева

    tokens = tokenize(query)
    return parse(tokens)


class Index:
    def __init__(self, index_file: str):
        self.inverted_index = {}
        with codecs.open(index_file, mode='r', encoding='utf-8') as f:
            for line in f:
                index = line.split('\t')[0]
                text = line.split('\t')[2]
                header = line.split('\t')[1]
                for word in text.split() + header.split():
                    postings = self.inverted_index.setdefault(word, set())
                    postings.add(index)

    def get(self, key, default=None):
        return self.inverted_index.get(key, default)

    def values(self):
        return self.inverted_index.values()


class QueryTree:
    def __init__(self, qid: int, query: str):
        self.qid = qid
        self.tree = parse_query(query)

    def search(self, index: Index) -> tuple[int, set]:
        return self.qid, self.evaluate_tree(self.tree, index)

    @staticmethod
    def evaluate_tree(node, document_index):
        """
        Обход дерева и вычисление множества релевантных документов.
        :param node: Корневой узел дерева.
        :param document_index: Индекс документов (словарь термов и их соответствующих документов).
        :return: Множество релевантных документов.
        """
        if node is None:
            return set()

        if node.value.isalnum() or "_" in node.value:  # Термин
            return document_index.get(node.value, set())

        if node.value == '!':  # Отрицание
            all_docs = set(doc_id for term_docs in document_index.values() for doc_id in term_docs)
            return all_docs - QueryTree.evaluate_tree(node.left, document_index)

        if node.value == ' ':  # Конъюнкция
            return QueryTree.evaluate_tree(node.left, document_index) & QueryTree.evaluate_tree(node.right,
                                                                                                document_index)

        if node.value == '|':  # Дизъюнкция
            return QueryTree.evaluate_tree(node.left, document_index) | QueryTree.evaluate_tree(node.right,
                                                                                                document_index)


class SearchResults:
    def __init__(self):
        self.results = set()

    def add(self, found: tuple[int, set]):
        query_index, documents_indices = found
        for document_index in documents_indices:
            self.results.add(f"{query_index}, {document_index}")

    def print_submission(self, objects_file: str, submission_file: str) -> None:
        with codecs.open(submission_file, mode='w', encoding='utf-8') as submission_f:
            with codecs.open(objects_file, mode='r', encoding='utf-8') as objects_f:
                for line in objects_f:
                    if line.startswith('ObjectId'):
                        submission_f.write("ObjectId,Relevance\n")
                        continue
                    ObjectId, QueryId, DocumentId = line.strip().split(',')
                    if f"{QueryId}, {DocumentId}" in self.results:
                        submission_f.write(f"{ObjectId},1\n")
                    else:
                        submission_f.write(f"{ObjectId},0\n")


def main():
    # Command line arguments.
    parser = argparse.ArgumentParser(description='Homework: Boolean Search')
    parser.add_argument('--queries_file', required=True, help='queries.numerate.txt')
    parser.add_argument('--objects_file', required=True, help='objects.numerate.txt')
    parser.add_argument('--docs_file', required=True, help='docs.tsv')
    parser.add_argument('--submission_file', required=True, help='output file with relevances')
    args = parser.parse_args()

    # Build index.
    index = Index(args.docs_file)

    # Process queries.
    search_results = SearchResults()
    with codecs.open(args.queries_file, mode='r', encoding='utf-8') as queries_fh:
        for line in queries_fh:
            fields = line.rstrip('\n').split('\t')
            qid = int(fields[0])
            query = fields[1]

            # Parse query.
            query_tree = QueryTree(qid, query)

            # Search and save results.
            search_results.add(query_tree.search(index))

    # Generate submission file.
    search_results.print_submission(args.objects_file, args.submission_file)


if __name__ == "__main__":
    main()
