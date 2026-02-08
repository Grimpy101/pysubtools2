import collections
import typing

from ..subtitle.formatting import Color, FontFace, Formatting, TextSize


class HTMLRule(typing.TypedDict):
    tag: str
    attribute: typing.Optional[str]


class HTMLTagMark(typing.TypedDict):
    tag_string: str
    index: int


class HTMLInjector:
    def __init__(self, rules: typing.Dict[typing.Type[Formatting], HTMLRule]) -> None:
        self.rules: typing.Dict[typing.Type[Formatting], HTMLRule] = rules
        self.marks: typing.Dict[typing.Tuple[int, int, str], typing.Set[str]] = collections.defaultdict(set)
        self.ordering: typing.Dict[str, int] = {k["tag"]: i for i, k in enumerate(self.rules.values())}
    
    def _get_formatting_value(self, formatting: Formatting) -> typing.Optional[str]:
        if isinstance(formatting, Color):
            return formatting.to_hex()
        elif isinstance(formatting, FontFace):
            return formatting.face
        elif isinstance(formatting, TextSize):
            return str(formatting.size)
        return None
    
    def _formatting_to_mark(self, formatting: Formatting):
        rule = self.rules.get(formatting.__class__)
        if rule is None:
            return None
        tag_name = rule['tag']
        start = formatting.start
        end = formatting.end
        attribute_name = rule.get('attribute')
        attribute = ""
        if attribute_name is not None:
            value = self._get_formatting_value(formatting)
            attribute = f'{attribute_name}="{value}"'
        self.marks[(start, end, tag_name)].add(attribute)
    
    def clear(self):
        self.marks.clear()
    
    def add_formattings(self, formattings: typing.List[Formatting]):
        for formatting in formattings:
            self._formatting_to_mark(formatting)
    
    def inject(self, text: str) -> str:
        tags: typing.List[typing.Tuple[int, int, str]] = []
        for mark, attributes in self.marks.items():
            start = mark[0]
            end = mark[1]
            tag = mark[2]
            attributes = list(attributes)
            attributes.sort()
            attributes_string = " ".join(attributes)
            
            start_tag = f'<{tag}'
            if attributes_string:
                start_tag += " " + attributes_string
            start_tag += ">"
            end_tag = f'</{tag}>'
            start_index = self.ordering.get(tag, 0)
            end_index = len(self.ordering) - start_index
            tags.append((start, start_index, start_tag))
            tags.append((end, end_index, end_tag))

        tags.sort(key=lambda x: (x[0], x[1]))
        
        for tag in reversed(tags):
            text = text[:tag[0]] + tag[2] + text[tag[0]:]
        return text