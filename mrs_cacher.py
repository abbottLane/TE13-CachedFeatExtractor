#!/bin/python3

"""%prog [--help] <e1> <e1_begin> <e1_end> <e2> <e2_begin> <e2_end> [<"sentence">]"""

import sys
from delphin.interfaces import ace
from delphin.mrs import simplemrs

__author__ = 'Martin J. Horn'


def format_features(features, key):
    str = key+"=+="
    for feat in features:
        str += feat + "#-#"
    str = str[:-3]

    return str


def extract_features(e1, e1_b, e1_e, e2, e2_b, e2_e, ace_result, reversed):
    # print("a1"+ace_result)
    features = []
    mrs = simplemrs.loads_one(ace_result)
    # print("mrs obj:" + str(mrs))
    ep_1, ep_2 = None, None
    for ep in mrs.eps():
        # print("an ep:" + str(ep))
        # print("is (ep.cfrom=", ep.cfrom, ") <= (e1_b=", e1_b+1, ") <= (ep.cto",
        #       ep.cto, ")? ", ep.cfrom <= e1_b <= ep.cto,
        #       " AND, (ep.pred.pos == 'n' or ep.pred.pos == 'v')? ",
        #       (ep.pred.pos == 'n' or ep.pred.pos == 'v'))
        if ep.cfrom <= e1_b + 1 <= ep.cto and (ep.pred.pos == 'n' or ep.pred.pos == 'v' or ep.pred.pos == 'a'):
            # print(str(ep) + "matched with " ,str(e1))
            ep_1 = ep
            continue
        elif ep.cfrom <= e2_b + 1 <= ep.cto and (ep.pred.pos == 'n' or ep.pred.pos == 'v' or ep.pred.pos == 'a'):
            # print(str(ep) + "matched with " ,str(e2))
            ep_2 = ep
            break
            # if ep:
            #     ep_1=ep
            #     #print("ep1 declared")
            # if ep:
            #     ep_2=ep
            #     #print("ep2 declared")

    # print("a2")
    if ep_1 and ep_2:
        if reversed:
            e1_tag = "e2"
            e2_tag = "e1"
        else:
            e1_tag = "e1"
            e2_tag = "e2"
        # print("a3")
        feat_1 = e1_tag + "LEMMA=" + ep_1.pred.lemma
        feat_2 = e2_tag + "LEMMA=" + ep_2.pred.lemma
        features.append(feat_1)
        features.append(feat_2)
        for prop in mrs.properties(ep_1.iv):
            feat = e1_tag + prop + "=" + mrs.properties(ep_1.iv)[prop]
            features.append(feat)
        for prop in mrs.properties(ep_2.iv):
            feat = e2_tag + prop + "=" + mrs.properties(ep_2.iv)[prop]
            features.append(feat)

        # Direct argument finding (currently obsolete)
        # args_1 = mrs.args(ep_1.nodeid)
        # args_2 = mrs.args(ep_2.nodeid)
        # feat = None
        # print("a4")
        # for arg in args_1:
        #     if ep_2.label == args_1[arg] or args_2['ARG0'] == args_1[arg]:
        #         feat = "e1#"+ep_1.pred.pos+"["+arg+"#e2#"+ep_2.pred.pos + "]"
        #         #print(feat)
        #         features.append(feat)
        # if not feat:
        #     for arg in args_2:
        #         if ep_1.label == args_2[arg] or args_1['ARG0'] == args_2[arg]:
        #             feat = "e2#"+ep_2.pred.pos+"[#"+arg+"#e1#"+ep_1.pred.pos + "]"
        #             #print(feat)
        #             features.append(feat)
        # print("a5")

        paths = find_paths(mrs, ep_1, ep_2, e1_tag, e2_tag, "")

        if paths:
            shortest_path = paths[0]
            for path in paths:
                if len(path.split(",")) < len(shortest_path.split(",")):
                    shortest_path = path
        else:
            shortest_path = "NO_PATH"
        features.append("PATH=" + shortest_path)

    # print("a6")
    return features


seen_ids = set()


def find_paths(mrs, ep_1, ep_2, e1_tag, e2_tag, cur_path, count=0):
    # Recursive path search using incoming args of second event
    paths = []
    if len(cur_path) == 0:
        if ep_2.pred.pos:
            cur_path = e2_tag + "#" + ep_2.pred.pos
        else:
            cur_path = e2_tag + "#" + "NO_POS"
            # Debug line: pred name
            # cur_path = ep_2.pred.string.strip("\"")
    else:
        if ep_2.pred.pos:
            cur_path = ep_2.pred.pos + "," + cur_path
        else:
            cur_path = "NO_POS," + cur_path
            # Debug line: pred name
            # cur_path = ep_2.pred.string.strip("\"") + "," + cur_path
    in_args = mrs.incoming_args(ep_2.nodeid)

    for node_id in in_args:
        global seen_ids
        if node_id not in seen_ids and count < 10:
            if mrs.ep(node_id).label != ep_1.label and mrs.ep(node_id).iv != ep_1.iv:
                for arg in in_args[node_id]:
                    prefix = arg + "#"
                    break
                seen_ids.add(node_id)
                count += 1
                paths += find_paths(mrs, ep_1, mrs.ep(node_id), e1_tag, e2_tag, prefix + cur_path, count)
            else:
                for arg in in_args[node_id]:
                    prefix = arg + "#"
                    break
                if mrs.ep(node_id).pred.pos:
                    cur_path = e1_tag + "#" + mrs.ep(node_id).pred.pos + "," + prefix + cur_path
                else:
                    cur_path = e1_tag + "#" + "NO_POS," + prefix + cur_path
                # Debug line: pred name
                # cur_path = mrs.ep(node_id).pred.string.strip("\"") + "," + prefix + cur_path
                paths.append(cur_path)
        else:
            paths.clear()

    return paths


def chop_sentence(sentence, e1_e, e2_e):
    new_sentence = None
    for i, char in enumerate(sentence):
        if char == ',' and i > e1_e and i > e2_e:
            if i > 0:
                if sentence[i-1] == ' ':
                    new_sentence = sentence[:i-1]
                else:
                    new_sentence = sentence[:i]
                new_sentence += '.'

                return new_sentence

    return new_sentence

COUNT = 0


def run_ace(sentence):
    global COUNT
    ace_bin = "/Applications/ace/ace-0.9.22/ace"
    erg_file = "/Applications/ace/ace-0.9.22/erg-1214-osx-0.9.22.dat"
    # ace_bin = "/home/wlane/Applications/ace-0.9.23/ace"
    # erg_file = "/home/wlane/Applications/ace-0.9.23/erg-1214-x86-64-0.9.23.dat"
    # ace_bin = "/home2/wlane/mrs-575/ace/ace"
    # erg_file = "/home2/wlane/mrs-575/ace/erg-1214-x86-64-0.9.22.dat"

    # ace_bin = "/Applications/ace/ace-0.9.22/ace"
    # erg_file = "/Applications/ace/ace-0.9.22/erg-1214-osx-0.9.22.dat"

    print("Running Ace " + str(COUNT))
    COUNT += 1
    results = ace.parse(erg_file, sentence, cmdargs=['-n', '1'], executable=ace_bin)['RESULTS']
    if results:
        res1 = results[0]['MRS']
    else:
        res1 = None

    return res1


def read_doc(e1, e1_begin, e1_end, e2, e2_begin, e2_end, file_name=None):
    reversed = False
    # Ensure e1 occurs first, e2 occurs second
    if int(e1_begin) < int(e2_begin):
        e1_string = e1
        e1_begin_sent = int(e1_begin)
        e1_end_sent = int(e1_end)
        e2_string = e2
        e2_begin_sent = int(e2_begin)
        e2_end_sent = int(e2_end)
    else:
        reversed = True
        e1_string = e2
        e1_begin_sent = int(e2_begin)
        e1_end_sent = int(e2_end)
        e2_string = e1
        e2_begin_sent = int(e1_begin)
        e2_end_sent = int(e1_end)

    # Check for specified input file
    if file_name:
        sent = file_name
        # # Read sentence from file
        # with open(file_name, 'r') as doc:
        #     doc_text = doc.read()
        #     sent = doc_text.strip()
    else:
        # Read sentence from stdin
        sent = input()

    return e1_string, e1_begin_sent, e1_end_sent, e2_string, e2_begin_sent, e2_end_sent, sent, reversed


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser(__doc__)
    options, args = parser.parse_args()

    cached_file_path = "Data/cachedSentences.eval.FULL.out"
    # cached_file_path = "/home2/wlane/mrs-575/TE13-CachedFeatExtractor/Data/cachedSentences.out"

    with open(cached_file_path) as file:
        sentences = file.readlines()

    # To collect the lines of final output
    # list_of_output_lines = list()

    f = open("Data/cachedMRSs-sent_reduction.eval.out", "w")

    prev_sent = None
    prev_res = None

    # per line, send each sentence to the erg
    for sentence in sentences:
        tokens = sentence.split("#-#")
        e1 = tokens[0]
        e1_b = tokens[1]
        e1_e = tokens[2]
        e2 = tokens[3]
        e2_b = tokens[4]
        e2_e = tokens[5]
        sent = tokens[6].rstrip("\n")

        if sent == prev_sent and prev_res:
            res = prev_res
        else:
            # In the output file of this program, feature sets will be structured as: key=+=feat1#-#feat2#-#feat3#-#etc...
            key = e1+e1_b+e1_e+e2+e2_b+e2_e+sent

            e1, e1_b, e1_e, e2, e2_b, e2_e, sent, reversed = read_doc(e1, e1_b, e1_e, e2, e2_b, e2_e, sent)

            res = run_ace(sent)
            if not res:
                new_sent = chop_sentence(sent, e1_e, e2_e)
                if new_sent:
                    res = run_ace(new_sent)

        # list_of_output_lines.append(res)

        f.write(str(res) + "\n")

        prev_sent = sent
        prev_res = res

        # print(res)
        # if res:
        #     feats = extract_features(e1, e1_b, e1_e, e2, e2_b, e2_e, res,reversed)
        #     formatted_feat = format_features(feats, key)
        #     list_of_output_lines.append(formatted_feat)
        #     #debug
        #     print(formatted_feat)
        # else:
        #     list_of_output_lines.append("NO_PARSE")
        #     #debug
        #     print("NO_PARSE")

    # Write features to output file
    # for line in list_of_output_lines:
    #     f.write(str(line)+"\n")

    f.close()
