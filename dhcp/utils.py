import re


def camelcase_to_underscore(camelcase: str) -> str:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camelcase)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    return s2.lower()


def camelcase_to_dash(camelcase: str) -> str:
    return camelcase_to_underscore(camelcase).replace('_', '-')
