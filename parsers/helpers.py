def text_or_none(el, tag):
    child = el.find(tag)
    return child.text if child is not None else None
