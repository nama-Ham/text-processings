# -*- coding: utf-8 -*-
import MeCab
import sqlite3
import re
import random
import numpy as np
from collections import namedtuple


Word = namedtuple('Word', 'wordid lang lemma pron pos')
Sense = namedtuple('Sense', 'synset wordid lang rank lexid freq src')
Synset = namedtuple('Synset', 'synset pos name src')
#SynsetDef = namedtuple('SynsetDef', 'synset lang defi sid')
conn = sqlite3.connect("../dict/synonym/wnjpn.db")

def get_word(lemma):
    cur = conn.execute("select * from word where lemma=?", (lemma,))
    return [Word(*row) for row in cur]

def get_senses(word, lang="jpn"):
    cur = conn.execute("select * from sense where wordid=? and lang=?", (word.wordid, lang))
    return [Sense(*row) for row in cur]

def get_words_from_synset(synset, word, lang):
    cur = conn.execute("select word.* from sense, word where synset=? and word.lang=? and sense.wordid=word.wordid and word.wordid<>?;", (synset, lang, word.wordid))
    return [Word(*row) for row in cur]

def search_synonyms(word):
    wobj = get_word(word)
    synonym_list = []
    if wobj:
        senses = get_senses(wobj[0])
        for s in senses:
            synonyms = get_words_from_synset(s.synset, wobj[0], "jpn")
            for syn in synonyms:
                if syn.lemma not in synonym_list:
                    synonym_list.append(syn.lemma)
    return synonym_list


def choose_synonym(word):
    synonym = word
    pos, basic = analyze_pos(word)
    synonyms = search_synonyms(word)
    idxs = np.arange(0, len(synonyms), 1)
    np.random.shuffle(idxs)
    for idx in idxs:        
        synonym_pos, synonym_basic = analyze_pos(synonyms[idx])
        if synonym_pos == pos and synonym_basic == basic:
            synonym = synonyms[idx]
            break
    return synonym


def transform(basic, conjugate):
    pos, a = analyze_pos(basic)
    target_verb = None
    dict_file = None
    if pos == "形容詞":
        dict_file = "Adj"
    elif pos == "動詞":
        dict_file = "Verb"
    elif pos == "副詞":
        dict_file = "Adverb"
    elif pos == "名詞":
        dict_file = "Noun"


    with open("../dict/pos/" + dict_file + ".csv", "rb") as f:
        verbs = f.readlines()
    for v in verbs:
        vinfo = v.decode('euc_jp',errors ='ignore').split(",")
        conj = vinfo[9]
        basicform = vinfo[10]
        if basicform == basic and conj == conjugate:
            target_verb = vinfo[0]
            break
    return target_verb

def analyze_pos(word):
    m = MeCab.Tagger()
    node = m.parseToNode(word)
    p,kb = None, None
    count = 0
    while node:
        pos = node.feature.split(",")[0]
        if pos != "BOS/EOS":
            p = pos
            count += 1
            if len(node.feature.split(",")) > 7:
                kb = node.feature.split(",")[7]
        node = node.next
    # 合成語の場合は品詞特定不可とする
    if count > 1:
        p,kb = None, None
    return p, kb


def convert_kata_to_hira(katakana):
    hira_tupple = ('あ','い','う','え','お','か','き','く','け','こ','さ','し','す','せ','そ','た','ち','つ','て','と','な','に','ぬ','ね','の','は','ひ','ふ','へ','ほ','ま','み','む','め','も','や','ゆ','よ','ら','り','る','れ','ろ','わ','を','ん','っ','ゃ','ゅ','ょ','ー','が','ぎ','ぐ','げ','ご','ざ','じ','ず','ぜ','ぞ','だ','ぢ','づ','で','ど','ば','び','ぶ','べ','ぼ','ぱ','ぴ','ぷ','ぺ','ぽ')
    kata_tupple = ('ア','イ','ウ','エ','オ','カ','キ','ク','ケ','コ','サ','シ','ス','セ','ソ','タ','チ','ツ','テ','ト','ナ','ニ','ヌ','ネ','ノ','ハ','ヒ','フ','ヘ','ホ','マ','ミ','ム','メ','モ','ヤ','ユ','ヨ','ラ','リ','ル','レ','ロ','ワ','ヲ','ン','ッ','ャ','ュ','ョ','ー','ガ','ギ','グ','ゲ','ゴ','ザ','ジ','ズ','ゼ','ゾ','ダ','ヂ','ヅ','デ','ド','バ','ビ','ブ','ベ','ボ','パ','ピ','プ','ペ','ポ')
    k_to_h_dict = dict()
    for i in range(len(hira_tupple)):
        k_to_h_dict[kata_tupple[i]] = hira_tupple[i]
    hiragana = ""
    for i in range(len(katakana)):
        hiragana += k_to_h_dict[katakana[i]]
    return hiragana


def mistake_ppp(ppp):
    substitute_ppp = ppp
    mistake_set = np.array([["が", "は"],["から", "より"]])
    target_pattern = mistake_set[np.any(mistake_set == ppp, axis = 1)]
    if len(target_pattern) > 0:
        the_other = target_pattern[np.where(target_pattern != ppp)]
        substitute_ppp = the_other[0]
    return substitute_ppp


m = MeCab.Tagger()

#text = "耳の外側と内側のノイズをマイクロフォンが検知。その音と釣り合うアンチノイズ機能が、あなたが聞く前にノイズを消し去ります。"
#text += "周囲の様子を聞いて対応したい時は、外部音取り込みモードに切り替えましょう。感圧センサーを長押しするだけです。"
#text = "Amazonで欲しいものを探しまわっていたら、最近は怪しい商品の日本語説明文のレベルアップがしてきたなと感じまして、日本語難しいのに勉強熱心だなと感心していたところです。そんな中、まだ発展途上だった日本語説明文が恋しくなったので自分でそういう文章を作ってみようと思いました。"
text = "このプログラム自体は役に立ちませんが、弱い日本語の特徴を掴むことは今後の日本語教育に有用ではと思いました。日本語を勉強中の外国人たちが書いた日本語の文章の傾向を学習しクラスタリングすることで間違えやすい日本語のパターンが明らかになって、そのそれぞれにあった日本語教育カリキュラムが作れたりしそうですね。"
'''
text = "包み込むようなサウンドを生み出すアクティブノイズキャンセリング"\
"周囲の音が聞こえて、今起きていることがわかる外部音取り込みモード"\
"装着感をカスタマイズできるように、ソフトな先細のシリコーン製イヤーチップを3つのサイズで用意"\
"耐汗耐水性能"\
"アダプティブイコライゼーションで音楽を耳の形に合わせて自動的に調節"\
"すべてのApple製デバイスで簡単に設定"\
"「Hey Siri」と声をかけるだけで瞬時にSiriへアクセス"\
"Wireless Charging Caseを使えば、バッテリー駆動時間は24時間以上"\
'''




node = m.parseToNode(text)

word_list = []
basic_list = []
pos_list = []
word_idx = 0 
prog_bar = "▪️"

while node:
    word = node.surface
    pos = node.feature.split(",")[0]
    conj = node.feature.split(",")[5]
    basic = node.feature.split(",")[6]
    if len(node.feature.split(",")) > 7:
        katakana = node.feature.split(",")[7]
    xfmd_word = None
    xfmd_basic = None
    # 変換パターン①：助詞の混同
    if pos == "助詞" and pos_list[word_idx - 1] == "名詞":
        xfmd_basic = basic
        xfmd_word = mistake_ppp(basic)
    # 変換パターン②：{過去形}+た => {現在形}
    elif pos == "助動詞" and word == "た":
        # 前の単語を現在形に置換する
        word_list[word_idx - 1] =  basic_list[word_idx - 1]
        xfmd_basic = ""
        xfmd_word = ""
    # 変換パターン③：同音類義語変換
    elif pos in ("動詞", "形容詞", "名詞"):
        xfmd_basic = basic
        if basic in ("*", "する"):
            xfmd_word = word
        else:
            synonym_basic = choose_synonym(basic)
            if pos in ("動詞", "形容詞"):
                if basic != "する":
                    xfmd_word = transform(synonym_basic, conj)
            else:
                xfmd_word = synonym_basic
    # 変換なし
    else:
        xfmd_basic = basic
        xfmd_word = word
    pos_list.append(pos)
    basic_list.append(xfmd_basic)
    word_list.append(xfmd_word)
    word_idx += 1;
    prog_per = f"{'{:.1f}'.format(2*word_idx/len(text)*100)} %: "
    prog_bar += "▪️"
    print(f"{prog_per}:{prog_bar}")
    node = node.next


xfmd_word_str = u"".join(word_list)
print(text)
print("|")
print("|")
print("↓")
print(xfmd_word_str)

