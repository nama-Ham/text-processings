# -*- coding: utf-8 -*-
import MeCab
import sqlite3
import re
import random
import csv


def confirm_pos(word, pos):
    result = None
    poss = analyze_pos(word)
    for p in poss:
        if p["pos"] == pos:
            result = p
    return result


def transform(pos, basic, conjugate):
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
    elif pos == "助詞":
        dict_file = "Postp"

    with open("dict/" + dict_file + ".csv", "rb") as f:
        verbs = f.readlines()
    for v in verbs:
        vinfo = v.decode('euc_jp',errors ='ignore').split(",")
        conj = vinfo[9]
        basicform = vinfo[10]
        if basicform == basic and conj == conjugate:
            target_verb = vinfo[0]
            break
    return target_verb



def search_sim_words(word):
    conn = sqlite3.connect("wnjpn.db")
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


def confirm_pos(word):
    m = MeCab.Tagger()
    node = m.parseToNode(word)
    p = None
    while node:
        pos = node.feature.split(",")[0]
        if pos != "BOS/EOS":
            p = pos
            break
        node = node.next
    return p


def choose_sim_word(words, pos):
    while True:
        r_idx = random.randint(0, len(words)-1)
        c_word = words[r_idx]
        sim_word_pos = confirm_pos(c_word)
        if sim_word_pos == pos:
            break
    return c_word



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


m = MeCab.Tagger()

#text = "英語の勉強をしていて、うーん自分の英語ってどう聞こえているのかなと気になったので、日本語を弱らせてみました"
#text = "自分の日本語を弱らせてみようかなと思いました。なんの役にも立たない記事でごめんなさい。"
text = "英語の勉強をしていて、うーん自分の英語ってどう聞こえているのかなと気になったので、自分の日本語を弱らせてみようかなと思いました。なんの役にも立たない記事でごめんなさい。"
node = m.parseToNode(text)

word_list = []
basic_list = []
word_idx = 0 

while node:
    word = node.surface
    pos = node.feature.split(",")[0]
    #conj = node.feature.split(",")[5]
    org = node.feature.split(",")[6]
    katakana = node.feature.split(",")[7]
    xfmd_word = None
    # 文頭・文末の空白の場合
    if word == "":
        xfmd_word = word
        # 基本形を保存
        basic_list.append(org)
        # word_list.append(xfmd_word)
    # それ以外の場合
    else:
        # 変換パターン①：{過去形}+た => {現在形}
        if word == "た" and pos == "助動詞":
            # 前の単語を現在形に置換する
            word_list[word_idx - 1] =  basic_list[word_idx - 1]     
            basic_list.append("")
            xfmd_word = ""
            #word_list.append("")
        else:
            # 記号は変換しない
            if pos == "記号":
                basic_list.append(org)
                xfmd_word = word
            # 変換パターン②：{漢字} => {ひらがな}
            else:
                basic_list.append(org)
                xfmd_word = convert_kata_to_hira(katakana)
                #word_list.append(xfmd_word)
    word_list.append(xfmd_word)
    word_idx += 1;
    node = node.next

xfmd_word_str = u"".join(word_list)
print(xfmd_word_str)