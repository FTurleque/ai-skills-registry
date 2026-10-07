"""Corpus de caracterisation : divisions par un compteur, avec ou sans test de valeur sur ce compteur."""


def bare_guarded(values):
    count = len(values)
    if count:
        return sum(values) / count
    return 0


def bare_unguarded(values):
    count = len(values)
    return sum(values) / count


class Stats:
    def __init__(self, size, count, total):
        self.size = size
        self.count = count
        self.total = total

    def guarded(self):
        if self.count:
            return self.size / self.count
        return 0

    def guarded_by_negation(self):
        if not self.count:
            return 0
        return self.size / self.count

    def guarded_by_conditional(self):
        return self.size / self.count if self.count else 0

    def unguarded(self):
        return self.size / self.count

    def guard_on_another_name(self):
        if self.total:
            return self.size / self.count
        return 0

    def guard_on_a_longer_name(self):
        if self.count_diff:
            return self.size / self.count
        return 0

    def guarded_with_and(self):
        if self.count and self.size:
            return self.size / self.count
        return 0

    def guarded_with_or(self):
        if not self.count or self.size < 0:
            return 0
        return self.size / self.count

    def guarded_in_elif(self, mode):
        if mode:
            return 0
        elif self.count:
            return self.size / self.count
        return 0

    def guarded_in_while(self):
        while self.count:
            return self.size / self.count
        return 0

    def one_divisor_guarded_the_other_not(self):
        if self.count:
            return self.size / self.count + self.size / self.total
        return 0
