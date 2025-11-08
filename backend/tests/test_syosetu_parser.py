from app.syosetu.parser import parse_chapter


MODERN_HTML = """
<html>
<body>
<h1 class="p-novel__title p-novel__title--rensai">幼年期　五歳の夏</h1>
<div class="p-novel__body">
<div class="js-novel-text p-novel__text">
<p id="L1">　ライン三重帝国は中央大陸西部の北方における古豪であり、広大な版図を誇る君主制国家であった。</p>
<p id="L2"><br></p>
<p id="L3">　三つの広範な領地を誇る皇統家が、選帝権を持つ選帝侯家と共同した互選で皇帝を選出することにより、安定した統治を実現し、五〇〇年の歴史を積み重ね未だ揺らがぬ大国。</p>
</div>
</div>
</body>
</html>
"""


def test_parse_chapter_modern_layout():
    title, text = parse_chapter(MODERN_HTML)
    assert title == "幼年期　五歳の夏"
    assert "ライン三重帝国" in text
    assert "三つの広範な領地" in text
