# -*- coding: utf-8 -*-
import MeCab
import sqlite3
import re
import random
import numpy as np


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
    #elif pos == "助詞":
    #    dict_file = "Postp"

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


def search_synonyms(word):
    conn = sqlite3.connect("../dict/synonym/wnjpn.db")
    cur = conn.execute("select wordid from word where lemma='%s'" % word)
    word_id = -1
    for row in cur:
        word_id = row[0]

    similar_words = []
    cur = conn.execute("select synset from sense where wordid='%s'" % word_id)
    synsets = []
    for row in cur:
        synsets.append(row[0])

    # 概念に含まれる単語を検索
    for synset in synsets:
        cur3 = conn.execute("select wordid from sense where (synset='%s' and wordid!=%s)" % (synset,word_id))
        for row3 in cur3:
            target_word_id = row3[0]
            cur3_1 = conn.execute("select lemma from word where wordid=%s" % target_word_id)
            for row3_1 in cur3_1:
            	# 全角文字のみでユニークな類義語のみ抽出
                if re.match(r'[^\x01-\x7E]', row3_1[0]) and row3_1[0] not in similar_words:
                    similar_words.append(row3_1[0])
    return similar_words


def choose_synonym(word):
    synonym = word
    pos, basic = analyze_pos(word)
    synonyms = search_synonyms(word)
    print(synonyms)
    idxs = np.arange(0, len(synonyms), 1)
    np.random.shuffle(idxs)
    for idx in idxs:        
        synonym_pos, synonym_basic = analyze_pos(synonyms[idx])
        if synonym_pos == pos and synonym_basic == basic:
            synonym = synonyms[idx]
            break
    return synonym


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
    mistake_set = np.array([["が", "は"],["から", "より"], ['を', 'に']])
    target_pattern = mistake_set[np.any(mistake_set == ppp, axis = 1)]
    if len(target_pattern) > 0:
        the_other = target_pattern[np.where(target_pattern != ppp)]
        substitute_ppp = the_other[0]
    return substitute_ppp


m = MeCab.Tagger()

text = "耳の外側と内側のノイズをマイクロフォンが検知。その音と釣り合うアンチノイズ機能が、あなたが聞く前にノイズを消し去ります。"
text += "周囲の様子を聞いて対応したい時は、外部音取り込みモードに切り替えましょう。感圧センサーを長押しするだけです。"
node = m.parseToNode(text)

word_list = []
basic_list = []
pos_list = []
word_idx = 0 

while node:
    word = node.surface
    print(node.feature.split(","))
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
        if basic != "*":
            synonym_basic = choose_synonym(basic)
            if pos in ("動詞", "形容詞"):
                xfmd_word = transform(synonym_basic, conj)
            else:
                xfmd_word = synonym_basic
        else:
            xfmd_word = word
    # 変換なし
    else:
        xfmd_basic = basic
        xfmd_word = word
    pos_list.append(pos)
    basic_list.append(xfmd_basic)
    word_list.append(xfmd_word)
    word_idx += 1;
    node = node.next


#print(pos_list)
#print(basic_list)
print(word_list)
xfmd_word_str = u"".join(word_list)
print(text)
print("===>")
print(xfmd_word_str)

#basic = "聞く"
#print(analyze_pos(basic))
#synonym_basic = choose_synonym(basic)
#print(synonym_basic)
#xfmd_word = transform(synonym_basic, conj)
#print(xfmd_word)
