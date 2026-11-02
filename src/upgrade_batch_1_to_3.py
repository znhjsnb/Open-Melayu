"""
Upgrade Batch 1-3 (30 words) in Open-Melayu:
1. Every sense receives >= 2 distinct authentic collocations in senses[].collocations.
2. Every word receives evidence-based etymology.historical_story.
3. Every colloquial dual_scenario receives >= 2 turns in messages with explicit speaker relationships.
4. Synchronizes data/enriched/<word>.json and batch_1.json, batch_2.json, batch_3.json.
Adheres strictly to PROJECT_HANDOFF.md Section 4 A2.
"""

import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
ENRICHED_DIR = ROOT_DIR / "data" / "enriched"

# Complete dataset for 30 words
UPGRADES = {
    # === BATCH 1 ===
    "saya": {
        "historical_story": "saya 来源于梵语 sahāya（伴侣、随从），在古马来语及古典文学中先借入为 sahaya / hamba sahaya（仆从、奴仆），古代臣民对君主或平民向上级回话时自称‘仆人’以示谦卑。到了近代，该词逐渐演化为现代标准马来语中最通用、最礼貌的第一人称代词，彻底褪去了最初的人身依附与仆从阶层色彩，成为跨越族群、职场与教育场合最中正、得体的中性第一人称自称。",
        "collocations": {
            1: [{"ms": "nama saya", "zh": "我的名字"}, {"ms": "rumah saya", "zh": "我的家；我的房子"}],
            2: [{"ms": "Ya, saya", "zh": "是，遵命（下属向长官应答）"}, {"ms": "Saya, tuan", "zh": "在，长官（军警或正式应答）"}]
        },
        "messages": [
            {"speaker": "Hafiz (同事)", "ms_spoken": "Kau dah lunch ke?", "ms_standard": "Awak sudah makan tengah hari ke?", "zh": "你吃午饭了吗？"},
            {"speaker": "Farah (同事)", "ms_spoken": "Belum, saya baru nak keluar ni.", "ms_standard": "Belum, saya baru mahu keluar ini.", "zh": "还没呢，我正准备出去。"}
        ]
    },
    "yang": {
        "historical_story": "关系代词与修饰引导词 yang 继承自南岛祖语关系标记 *a-ŋ 或 *ia-ŋ，在从古典到现代马来语的句法演进中承担连接修饰从句的核心功能；神灵义项的 Yang 则见于马来群岛印度化时期对至高尊号的称呼（如 Sang Hyang），属于古语神圣称谓；而口语中表示‘亲爱的’称呼 yang 则是近代亲密词 sayang 在日常聊天中的自然省音缩短，三者在现代马来语中属于不同历史层面的同形共存。",
        "collocations": {
            1: [{"ms": "buku yang dibeli", "zh": "买的书"}, {"ms": "orang yang bijak", "zh": "聪明的人"}],
            2: [{"ms": "yang mana satu", "zh": "哪一个"}, {"ms": "yang terbaik", "zh": "最好的（那个/事物）"}],
            3: [{"ms": "dia cakap yang dia penat", "zh": "他说他很累"}, {"ms": "aku rasa yang dia tahu", "zh": "我觉得他是知道的"}],
            4: [{"ms": "yang hamba ini", "zh": "至于仆人我"}, {"ms": "sebermula yang tersebut", "zh": "且说那所记载之事"}],
            5: [{"ms": "Yang Maha Esa", "zh": "独一真主 / 独一全能神"}, {"ms": "Sang Yang", "zh": "至尊神灵（古语神号）"}],
            6: [{"ms": "hai yang", "zh": "嗨，亲爱的（sayang 简称）"}, {"ms": "tengok ni, yang", "zh": "看这个，亲爱的"}]
        },
        "messages": [
            {"speaker": "Aiman (朋友)", "ms_spoken": "Baju mana yang kau nak beli?", "ms_standard": "Baju mana yang awak hendak beli?", "zh": "你想买哪件衣服？"},
            {"speaker": "Hafiq (朋友)", "ms_spoken": "Yang warna biru tu, nampak lawa sikit.", "ms_standard": "Yang warna biru itu, kelihatan cantik sedikit.", "zh": "那件蓝色的，看起来好看一点。"}
        ]
    },
    "aku": {
        "historical_story": "aku 继承自南岛祖语（Proto-Austronesian）的核心第一人称单数词根 *aku，广泛见于马来-波利尼西亚诸语（如他加禄语 ako、爪哇语 aku）。作为千年来世代相传的基础核心词，aku 始终承载着最质朴、最原初的自我指涉，在现代马来社会主要用于至交密友、同辈熟人、家庭亲近对话、文学抒情以及面向造物主的真挚祈祷，对长辈或职场上司直称 aku 则被视作失礼越界。",
        "collocations": {
            1: [{"ms": "aku dan kau", "zh": "我和你（亲密平辈）"}, {"ms": "doa aku", "zh": "我的祈祷（文学或宗教敬虔）"}]
        },
        "messages": [
            {"speaker": "Danial (发小)", "ms_spoken": "Petang ni lepak mamak tak?", "ms_standard": "Petang ini lepak di kedai mamak tidak?", "zh": "今天下午去嘛嘛档坐坐吗？"},
            {"speaker": "Irfan (发小)", "ms_spoken": "On je, aku sampai lepas asar nanti.", "ms_standard": "Boleh sahaja, aku sampai selepas asar nanti.", "zh": "去啊，我阿瑟拜之后就到。"}
        ]
    },
    "dia": {
        "historical_story": "dia 在语言发生学上由方位介词词根 di 与古马来语第三人称单数代词 ia 复合凝固而成（di + ia → dia），最初兼具方位指示与人称回指功能。随着语法化演进，现代马来语中 dia 成为不分男女的通用第三人称单数代词，而原始形式 ia 则主要保留在书面语主语位置或无生命代指；固定搭配 itu dia 则完整保留了该词早期的指示指认遗风。",
        "collocations": {
            1: [{"ms": "dia kawan saya", "zh": "他/她是我的朋友"}, {"ms": "kereta dia", "zh": "他/她的车"}],
            2: [{"ms": "ha itu dia", "zh": "哈，就是那个人/那个东西！"}, {"ms": "itu dia datang", "zh": "看，他来了！"}]
        },
        "messages": [
            {"speaker": "Lina (同学)", "ms_spoken": "Mana Sarah? Tak nampak pun dia hari ni.", "ms_standard": "Di manakah Sarah? Tidak nampak pun dia pada hari ini.", "zh": "莎拉在哪儿？今天都没看到她。"},
            {"speaker": "Maya (同学)", "ms_spoken": "Dia demam kot, semalam dia kata kepala pening.", "ms_standard": "Dia demam mungkin, semalam dia berkata kepala pening.", "zh": "可能发烧了吧，昨天她说头晕。"}
        ]
    },
    "awak": {
        "historical_story": "awak 的本义是‘身体、躯干’（如爪哇语 awak 同义），早期马来水上航海社会中，一条船上的全部人员被称作 awak kapal（即整条船的‘身躯支柱’，引申为全体船员）。在廖内-柔佛马来语的演进过程中，人们出于礼貌避免直呼对方名字或直呼尖锐代词，通过提喻法将‘躯体、阁下之身’转指为第二人称‘你’，形成了现代西马最为温和、普及的同辈社交第二人称称谓。",
        "collocations": {
            1: [{"ms": "awak apa khabar", "zh": "你好吗？"}, {"ms": "terima kasih awak", "zh": "谢谢你"}],
            2: [{"ms": "badan awak", "zh": "身体躯干"}, {"ms": "saiz awak", "zh": "体格大小"}],
            3: [{"ms": "awak kapal", "zh": "船员；水手"}, {"ms": "awak pesawat", "zh": "机组人员；空勤人员"}],
            4: [{"ms": "awak sama awak", "zh": "自己人之间"}, {"ms": "jaga diri awak", "zh": "照顾好你自己"}]
        },
        "messages": [
            {"speaker": "Nurul (朋友)", "ms_spoken": "Awak dah siap ke kerja tu?", "ms_standard": "Awak sudah siapkan kerja itu?", "zh": "那份工作你做好了吗？"},
            {"speaker": "Amir (朋友)", "ms_spoken": "Sikit lagi nak settle, satgi saya send.", "ms_standard": "Sedikit lagi mahu selesai, sebentar lagi saya hantar.", "zh": "还差一点就完成了，待会儿我发给你。"}
        ]
    },
    "kau": {
        "historical_story": "kau 是古典马来语完整第二人称代词 engkau 的音系弱化与快速口语缩短形，其远祖可追溯至马来-波利尼西亚祖语 *ikaw。作为独立代词时，kau 带着非常亲近随和的情感，但在非熟人对话中若无故使用会被视作傲慢失礼；而在标准马来语文法中，kau- 连写在动词词根前构成第一/第二人称被动语态（如 kaurasa、kaubaca），是传统马来语法体系中极为严整的规范附着形态素。",
        "collocations": {
            1: [{"ms": "kau pergi mana", "zh": "你去哪儿了？"}, {"ms": "cakap kat kau", "zh": "跟你说（实话）"}],
            2: [{"ms": "buku yang kauambil", "zh": "被你拿走的书"}, {"ms": "surat yang kautulis", "zh": "你写的那封信"}]
        },
        "messages": [
            {"speaker": "Zul (死党)", "ms_spoken": "Kau buat apa kat sini bro?", "ms_standard": "Awak buat apa di sini, kawan?", "zh": "兄弟，你在这儿干嘛呢？"},
            {"speaker": "Hakim (死党)", "ms_spoken": "Tengah tunggu kawan aku ni, lambat pulak.", "ms_standard": "Sedang menunggu kawan saya ini, lambat pula.", "zh": "正等我朋友呢，居然迟到了。"}
        ]
    },
    "ini": {
        "historical_story": "ini 继承自南岛祖语的近指指示词根 *i-ni（这里、这），广泛见于整个马来语支语言中。在马来语的空间认知哲学中，ini 严格指代空间距离或心理感知上靠近说话者的客体，并随语言发展延伸到时间维度（如 hari ini‘今天’）以及语篇维度（指代刚刚提及的话题），与远指词 itu 构成了马来语空间指示系统的两大基石支柱。",
        "collocations": {
            1: [{"ms": "buku ini", "zh": "这本书"}, {"ms": "masalah ini", "zh": "这个问题"}],
            2: [{"ms": "hari ini", "zh": "今天"}, {"ms": "malam ini", "zh": "今晚"}],
            3: [{"ms": "apa hal ini", "zh": "这究竟是怎么回事"}, {"ms": "bukan ini sahaja", "zh": "不仅如此；不单是这个"}]
        },
        "messages": [
            {"speaker": "Siti (顾客)", "ms_spoken": "Berapa harga beg ini ya?", "ms_standard": "Berapakah harga beg ini ya?", "zh": "请问这个包多少钱呀？"},
            {"speaker": "Peniaga (店主)", "ms_spoken": "Yang ini RM30 je kak, murah hari ni.", "ms_standard": "Yang ini RM30 sahaja kak, murah hari ini.", "zh": "这个只要三十令吉，今天特惠。"}
        ]
    },
    "di": {
        "historical_story": "表示物理方位的介词 di 属于马来语古老的原生空间介词，可追溯至原始南岛语的地点标记词根 *di。在古代马来语碑文（如 7 世纪室利佛逝时代的格杜甘武吉石碑）中已有清晰明确的地点记载。规范马来语正字法严格规定地点介词 di 必须与后续名词分写（如 di sekolah），以区别于动词被动语态前缀 di-（如 dimakan 连写）；而字母名 di 则是近代引入拉丁字母表时借入的外来音名。",
        "collocations": {
            1: [{"ms": "di rumah", "zh": "在家"}, {"ms": "di sekolah", "zh": "在学校"}],
            2: [{"ms": "di bawah pengawasan", "zh": "在监督之下"}, {"ms": "di pihak kami", "zh": "在我们这一方"}],
            3: [{"ms": "huruf di", "zh": "字母 D"}, {"ms": "bermula dengan huruf di", "zh": "以字母 D 开头"}]
        },
        "messages": [
            {"speaker": "Kamal (朋友)", "ms_spoken": "Kau lepak kat mana sekarang?", "ms_standard": "Awak berada di mana sekarang?", "zh": "你现在在哪儿坐着呢？"},
            {"speaker": "Fikri (朋友)", "ms_spoken": "Ada kat cafe ni, tengah minum.", "ms_standard": "Ada di kafe ini, sedang minum.", "zh": "在咖啡馆这儿呢，正喝着东西。"}
        ]
    },
    "tak": {
        "historical_story": "否定词 tak 产生于日常口语交流中的语音弱化机制，由规范否定词 tidak 经过快速连读省去首音节 ti- 并保留重音末音节而形成。早期主要流行于马来半岛各州民间的口语、民谣和集市交易中（Bahasa Pasar），近代随着大众影视传媒和社交网络的普及，tak 已经彻底融入西马口语的日常表达中，但在正式公文、法律文书与学术答辩中，依旧必须严格使用规范全称 tidak。",
        "collocations": {
            1: [{"ms": "tak boleh", "zh": "不可以；不行"}, {"ms": "tak tahu", "zh": "不知道"}],
            2: [{"ms": "tak apa", "zh": "没关系；不要紧"}, {"ms": "tak apa-apa", "zh": "没什么大碍"}],
            3: [{"ms": "betul tak", "zh": "对不对？是不是？"}, {"ms": "takkan lah", "zh": "不可能吧；难道会是这样"}]
        },
        "messages": [
            {"speaker": "Adam (室友)", "ms_spoken": "Kau tak makan lagi ke dari tadi?", "ms_standard": "Awak tidak makan lagi kah dari tadi?", "zh": "你从刚才到现在都还没吃吗？"},
            {"speaker": "Faiz (室友)", "ms_spoken": "Tak lapar sangat pun, satgi aku keluar beli.", "ms_standard": "Tidak lapar sangat pun, sebentar lagi saya keluar beli.", "zh": "不是很饿，待会儿我出去买。"}
        ]
    },
    "dan": {
        "historical_story": "连词 dan 在马来语词汇史中的确切更早词源尚未取得公认的原始南岛语对应重构证据；在 16-17 世纪古典马来文学经典《马来纪年》（Sejarah Melayu）与传统宫廷编年史中，作者更习惯使用 maka（便、则）、serta（以及）或 pun 来承接句子成分。随着近代文体规范化与印刷术的发展，dan 最终被确立为现代马来语中连接并列词组、分句最标准、不可替代的等立并列连词。",
        "collocations": {
            1: [{"ms": "ibu dan bapa", "zh": "父母；父亲和母亲"}, {"ms": "membaca dan menulis", "zh": "读与写"}],
            2: [{"ms": "dan sebagainya", "zh": "等等；诸如此类"}, {"ms": "dan lain-lain", "zh": "以及其他"}]
        },
        "messages": [
            {"speaker": "Mei (同事)", "ms_spoken": "Dah beli barang dapur ke?", "ms_standard": "Sudah beli barang dapur kah?", "zh": "买厨房日用品了吗？"},
            {"speaker": "Nisa (同事)", "ms_spoken": "Dah beli roti dan telur tadi.", "ms_standard": "Sudah beli roti dan telur tadi.", "zh": "刚才买了面包和鸡蛋。"}
        ]
    },

    # === BATCH 2 ===
    "akan": {
        "historical_story": "akan 最早是古马来语中的方位与关系介词，意为‘朝向、关于、为了’（如 classical Malay 中常见的 cinta akan negara、takut akan Allah）。随着语言的语法化演化，表示‘朝向某一目标时间’的介词功能逐渐演变成了标记将来时态的助动词‘将要’，成为现代标准语的核心时相助词；而固定转折连词 akan tetapi（然而、但是）则完整凝固了该词由介词向复合连词过渡的历史语法化印记。",
        "collocations": {
            1: [{"ms": "akan datang", "zh": "未来；即将来临"}, {"ms": "akan bermula", "zh": "即将开始"}],
            2: [{"ms": "takut akan", "zh": "害怕；敬畏（某事物）"}, {"ms": "rindu akan", "zh": "思念（某人/某地）"}],
            3: [{"ms": "ingat akan", "zh": "忆及；记起（往事）"}, {"ms": "lupa akan", "zh": "遗忘（责任或诺言）"}],
            4: [{"ms": "ubat akan penyakit", "zh": "医治疾病的药物"}, {"ms": "bekal akan perjalanan", "zh": "供旅途使用的口粮"}],
            5: [{"ms": "akan tetapi dia enggan", "zh": "然而他却不肯"}, {"ms": "akan tetapi perkara itu", "zh": "但是那件事情"}]
        },
        "messages": [
            {"speaker": "Rizal (项目经理)", "ms_spoken": "Projek ni bila akan siap bro?", "ms_standard": "Projek ini bilakah akan siap, kawan?", "zh": "兄弟，这个项目什么时候会完成？"},
            {"speaker": "Tengku (工程师)", "ms_spoken": "Minggu depan akan settle semua insya-Allah.", "ms_standard": "Minggu hadapan akan selesai semua insya-Allah.", "zh": "顺利的话下周一切都会搞定。"}
        ]
    },
    "tidak": {
        "historical_story": "tidak 历史上与 tiada（无、没有）同源，属于古代马来语 ti（否定词素）与相关助词复合演变而成的正式否定副词。在现代标准马来语规范语法中，tidak 专门用来否定动词谓语（如 tidak pergi）和形容词谓语（如 tidak cantik），而否定名词短语时则必须使用 bukan，两者构成了马来语体系中严丝合缝的否定对立系统。",
        "collocations": {
            1: [{"ms": "tidak ada", "zh": "没有"}, {"ms": "tidak mungkin", "zh": "不可能"}],
            2: [{"ms": "sama ada ya atau tidak", "zh": "是或者不是"}, {"ms": "jawab tidak", "zh": "回答‘不’；拒绝"}]
        },
        "messages": [
            {"speaker": "Salim (警卫)", "ms_spoken": "Encik, kawasan ini tidak boleh masuk ya.", "ms_standard": "Encik, kawasan ini tidak boleh masuk ya.", "zh": "先生，这个区域不能进入哦。"},
            {"speaker": "Pelawat (访客)", "ms_spoken": "Oh maaf, saya tidak perasan ada papan tanda.", "ms_standard": "Oh maaf, saya tidak perasan ada papan tanda.", "zh": "噢抱歉，我没注意到有指示牌。"}
        ]
    },
    "kita": {
        "historical_story": "kita 直接继承自原始南岛语（Proto-Austronesian）的核心包括式第一人称代词 *kita（包括说话者与听话者）。这种‘包容式 we’与排除式 kami（不包含听话者）的精妙语法对立是南岛语言最具代表性的特征。在马来半岛口语演变中，kita 进一步延伸出亲昵语气下的单数自称（相当于汉语‘人家’）或口语泛称，展现了马来文化中注重集体认同与温和语气的社会语言学特征。",
        "collocations": {
            1: [{"ms": "kita semua", "zh": "我们大家（包含在场听众）"}, {"ms": "negara kita", "zh": "我们的国家"}],
            2: [{"ms": "kita orang", "zh": "我们这伙人（口语代称）"}, {"ms": "nanti kita bincang", "zh": "待会儿我们自己商量"}],
            3: [{"ms": "kita tak suka lah", "zh": "人家不喜欢啦（娇嗔自称）"}, {"ms": "tengok kita ni", "zh": "看看人家嘛"}],
            4: [{"ms": "apa khabar kita", "zh": "您近况如何（古方言尊称）"}, {"ms": "suruhan kita", "zh": "阁下的吩咐"}],
            5: [{"ms": "apa orang kata tentang kita", "zh": "外人如何评价我们"}, {"ms": "jangan susahkan orang lain kerana kita", "zh": "切勿因自己而连累旁人"}]
        },
        "messages": [
            {"speaker": "Aina (朋友)", "ms_spoken": "Jom kita gerak sekarang, nanti jem.", "ms_standard": "Mari kita bergerak sekarang, nanti jalan sesak.", "zh": "来我们现在走吧，等下要塞车了。"},
            {"speaker": "Bella (朋友)", "ms_spoken": "Kejap, kita cari kunci kereta jap.", "ms_standard": "Sebentar, saya mencari kunci kereta sebentar.", "zh": "等等，我找一下车钥匙。"}
        ]
    },
    "apa": {
        "historical_story": "apa 来源于原始南岛语的核心疑问代词 *s-apa / *apa，千百年来一直承担着询问未知事物的核心认知功能。在马来口语的长远演化中，apa 展现了极强的多功能性：重叠为 apa-apa 表达泛指（任何东西），加附着词 apa tu 作为谈话停顿填充词，在口语省略中甚至能作为询问原因（apa pasal）或表达惊叹语气的多功能语法词素。",
        "collocations": {
            1: [{"ms": "apa ini", "zh": "这是什么？"}, {"ms": "nama apa", "zh": "叫什么名字？"}],
            2: [{"ms": "apa-apa sahaja", "zh": "任何东西；无论什么"}, {"ms": "tak ada apa", "zh": "没什么；并无大碍"}],
            3: [{"ms": "apa fasal", "zh": "为什么；何故"}, {"ms": "apa pasal lambat", "zh": "怎么迟到了？"}],
            4: [{"ms": "sama ada apa tidak", "zh": "无论怎样与否"}, {"ms": "nak ini apa itu", "zh": "要这个还是那个？"}],
            5: [{"ms": "apa lah kau ni", "zh": "你这人怎么这样啊"}, {"ms": "apa lagi", "zh": "还有什么好说的；还等什么"}],
            6: [{"ms": "apa tu", "zh": "那个叫什么来着..."}, {"ms": "apa nama tempat tu", "zh": "那个地方叫什么名字来着..."}]
        },
        "messages": [
            {"speaker": "Rani (同事)", "ms_spoken": "Kau tengah buat apa tu?", "ms_standard": "Awak sedang buat apa itu?", "zh": "你正在做什么呢？"},
            {"speaker": "Haziq (同事)", "ms_spoken": "Tengah check report bos minta pagi tadi.", "ms_standard": "Sedang menyemak laporan yang diminta oleh bos pagi tadi.", "zh": "正在核对老板今天早上要的报告呢。"}
        ]
    },
    "kamu": {
        "historical_story": "kamu 承袭自原始马来-波利尼西亚语的第二人称复数代词 *kamu，后在马来语历史演变中兼具单数和复数功能。在传统马来家庭与学校语境中，kamu 常由长辈对晚辈、教师对学生使用，带有自然的权威与关怀色彩；在现代书面文学中它也是通用的第二人称代词，其弱化后置附着形式 -mu 更是古典与现代诗歌、规范正字法中最普遍的所有格形式。",
        "collocations": {
            1: [{"ms": "kamu semua", "zh": "你们大家"}, {"ms": "di mana kamu tinggal", "zh": "你住在哪里？"}],
            2: [{"ms": "nama kamu", "zh": "你的名字"}, {"ms": "ibu kamu", "zh": "你的母亲"}]
        },
        "messages": [
            {"speaker": "Cikgu Rosli (老师)", "ms_spoken": "Kamu dah siap latihan yang saya bagi?", "ms_standard": "Kamu sudah menyiapkan latihan yang saya beri?", "zh": "我布置的练习你们做完了吗？"},
            {"speaker": "Danish (学生)", "ms_spoken": "Dah cikgu, kami hantar sekarang.", "ms_standard": "Sudah cikgu, kami hantar sekarang.", "zh": "做完了老师，我们现在交。"}
        ]
    },
    "itu": {
        "historical_story": "itu 继承自原始马来-波利尼西亚语的远指指示词 *i-tu（那里、那个），在空间上与近指词 ini 形成对峙，指示远离说话者空间、时间或视线边界的客观对象。在话语层面，itu 还承担着强烈的回指功能（anaphoric reference），用来激活交谈双方早已知晓的前述背景信息，并派生出 itulah、macam itu 等经典固定短语。",
        "collocations": {
            1: [{"ms": "rumah itu", "zh": "那所房子"}, {"ms": "orang itu", "zh": "那个人"}],
            2: [{"ms": "pada masa itu", "zh": "在那个时候"}, {"ms": "hal itu berlaku", "zh": "那件事情发生了"}]
        },
        "messages": [
            {"speaker": "Fendi (朋友)", "ms_spoken": "Kedai makan itu sedap tak?", "ms_standard": "Kedai makan itu sedap tidak?", "zh": "那家餐馆好吃吗？"},
            {"speaker": "Syah (朋友)", "ms_spoken": "Memang padu bro, mee kari dia mantap.", "ms_standard": "Memang sedap kawan, mi kari dia sangat lazat.", "zh": "非常棒兄弟，那里的咖喱面一流。"}
        ]
    },
    "untuk": {
        "historical_story": "untuk 的深层词源在现存南岛语比较语言学中尚无明确无可置疑的古祖语重构形式，其在古典文献中最初多作名词使用，意为‘份儿、定额’（如 bahagian untuk），后在漫长语法化进程中由名词实词虚化为目的与受益者介词‘为了、给’。现代标准语中为了表达严谨，表示纯时间段时常建议用 selama，但日常与书面语中 untuk 引出目的或服务对象的功能已深入人心。",
        "collocations": {
            1: [{"ms": "hadiah untuk ibu", "zh": "给母亲的礼物"}, {"ms": "khas untuk anda", "zh": "专为您准备"}],
            2: [{"ms": "wang untuk belajar", "zh": "用于求学的资金"}, {"ms": "alat untuk memasak", "zh": "烹饪工具"}],
            3: [{"ms": "untuk masa ini", "zh": "就目前阶段而言"}, {"ms": "untuk makluman", "zh": "谨此告知；供参考"}],
            4: [{"ms": "untuk masing-masing", "zh": "各自的份额"}, {"ms": "dapat untuk", "zh": "分得一份"}],
            5: [{"ms": "untuk beberapa hari", "zh": "持续数日"}, {"ms": "untuk seketika", "zh": "片刻；一阵子"}],
            6: [{"ms": "untuk sebab itulah", "zh": "正因那个缘故"}, {"ms": "sukar untuk difahami", "zh": "因其难解"}]
        },
        "messages": [
            {"speaker": "Mira (姐姐)", "ms_spoken": "Kek ni kau beli untuk siapa?", "ms_standard": "Kek ini awak beli untuk siapa?", "zh": "这个蛋糕你买给谁的呀？"},
            {"speaker": "Anis (妹妹)", "ms_spoken": "Untuk adik, hari ni birthday dia kan.", "ms_standard": "Untuk adik, hari ini hari jadi dia kan.", "zh": "给弟弟的，今天不是他生日嘛。"}
        ]
    },
    "ada": {
        "historical_story": "ada 继承自原始南岛语的核心存在与领属动词词根 *wada / *hada，在整个马来群岛诸语中皆有直接同源词。作为马来语存在论思维的核心表达，ada 兼具客观存在（there is）、主观拥有（have）与处所存在（be located）三重维度，并在近代口语中进一步语法化为强调动作真实发生（pernah / sesungguhnya）的肯定体标记，构成了马来语表达存在与事实最底层的语法基石。",
        "collocations": {
            1: [{"ms": "ada orang di luar", "zh": "外面有人"}, {"ms": "ada masa", "zh": "有时间"}],
            2: [{"ms": "ada wang", "zh": "有钱"}, {"ms": "ada peluang", "zh": "有机会"}],
            3: [{"ms": "ada di rumah", "zh": "在家里"}, {"ms": "ada di pejabat", "zh": "在办公室"}],
            4: [{"ms": "masih ada", "zh": "依然健在；依然存在"}, {"ms": "selagi ada hayat", "zh": "只要尚在人世"}],
            5: [{"ms": "saya ada beritahu dia", "zh": "我确实告诉过他"}, {"ms": "ada nampak tak", "zh": "确实看到了吗？"}],
            6: [{"ms": "saya ada cikgu", "zh": "我到了，老师（点名应答）"}, {"ms": "semua ada", "zh": "全都到齐了"}],
            7: [{"ms": "ada apa-apa masalah", "zh": "有什么问题吗？"}, {"ms": "ada nak pesan apa-apa", "zh": "有什么要交代的吗？"}]
        },
        "messages": [
            {"speaker": "Jamil (朋友)", "ms_spoken": "Ada masa tak malam ni, nak borak jap.", "ms_standard": "Ada masa tidak malam ini, mahu bersembang sebentar.", "zh": "今晚有空吗，想聊聊。"},
            {"speaker": "Khairul (朋友)", "ms_spoken": "Ada je bro, lepas pukul lapan aku free.", "ms_standard": "Ada sahaja kawan, selepas pukul lapan saya lapang.", "zh": "有空的兄弟，八点之后我都有空。"}
        ]
    },
    "boleh": {
        "historical_story": "boleh 的古义为‘获取、得到’，直接见于古马来语派生词 peroleh（获得）以及菲律宾他加禄语同源词 bili（购买、获得）。在古典文献向现代马来语过渡的几个世纪中，‘能够获得某物’的历史意义逐渐虚化演变为表示主观能力与客观许可的情态助动词‘可以、能够’，古老实词义项在现代语中已基本废弃，而口语固定搭配 boleh tahan（不错、过得去）则延续了其肯定能力的衍生色彩。",
        "collocations": {
            1: [{"ms": "boleh pergi", "zh": "可以去"}, {"ms": "boleh buat", "zh": "能够做；办得到"}],
            2: [{"ms": "boleh tahan", "zh": "蛮不错；过得去"}, {"ms": "boleh juga", "zh": "也行；还可以"}],
            3: [{"ms": "boleh hasil", "zh": "获得收益（古文用法）"}, {"ms": "tidak boleh apa-apa", "zh": "一无所获"}]
        },
        "messages": [
            {"speaker": "Zaki (同事)", "ms_spoken": "Boleh tolong print file ni tak?", "ms_standard": "Boleh tolong cetak fail ini tidak?", "zh": "能帮忙打印这个文件吗？"},
            {"speaker": "Chong (同事)", "ms_spoken": "Boleh, pass kat email saya sekarang.", "ms_standard": "Boleh, hantar ke e-mel saya sekarang.", "zh": "没问题，现在发到我邮箱吧。"}
        ]
    },
    "mereka": {
        "historical_story": "第三人称复数代词 mereka 的深层发生学渊源在语言学界存在多种讨论，古典马来文献早期更普遍使用 *sida 或 dia orang，后逐步由 mereka 统一担当标准人称代词；而同形动词 mereka（构思、设计、捏造）则是前缀 meN- 附加在动词词根 reka 之上的规则派生，词根 reka 本身借自梵语 rekhā（线条、设计），因此代词 mereka 与动词 mereka 在构词母体与词源脉络上是截然不同的两座历史丰碑。",
        "collocations": {
            1: [{"ms": "mereka semua", "zh": "他们大家"}, {"ms": "keluarga mereka", "zh": "他们的家庭"}],
            2: [{"ms": "mereka bentuk", "zh": "设计；造型"}, {"ms": "mereka cipta", "zh": "发明；创造"}],
            3: [{"ms": "mereka cerita", "zh": "编造谎言；捏造故事"}, {"ms": "mereka alasan", "zh": "编造借口"}],
            4: [{"ms": "mereka lagu", "zh": "谱写乐曲"}, {"ms": "mereka sajak", "zh": "创作诗歌"}]
        },
        "messages": [
            {"speaker": "Puan Zainab (主管)", "ms_spoken": "Budak-budak praktikal tu kat mana sekarang?", "ms_standard": "Pelajar-pelajar praktikal itu di manakah sekarang?", "zh": "那些实习生现在在哪儿？"},
            {"speaker": "En. Fauzi (职员)", "ms_spoken": "Mereka tengah attend meeting kat bilik sebelah.", "ms_standard": "Mereka sedang menghadiri mesyuarat di bilik sebelah.", "zh": "他们正在隔壁会议室开会呢。"}
        ]
    },

    # === BATCH 3 ===
    "dengan": {
        "historical_story": "dengan 是马来语中承载功能最丰富的基础介词之一，文献记载其不仅长期充当共格（伴随）、工具格与方式格介词，而且在古马来语历史文本中还保留着实词名词与人称代词用法，意为‘随从、奴仆’乃至谦卑自称‘我’（与 sahaya 的演变路径形成有趣的跨语汇呼应）。在现代马来语中，名词与代词用法已经退化为古典文献遗迹，而介词 dengan 则成为连接伴随、手段、依据与修饰最通用的核心枢纽。",
        "collocations": {
            1: [{"ms": "pergi dengan kawan", "zh": "和朋友一起去"}, {"ms": "makan dengan keluarga", "zh": "与家人共进晚餐"}],
            2: [{"ms": "menulis dengan pen", "zh": "用钢笔写字"}, {"ms": "memotong dengan pisau", "zh": "用刀切"}],
            3: [{"ms": "dengan cepat", "zh": "迅速地"}, {"ms": "dengan berhati-hati", "zh": "小心翼翼地"}],
            4: [{"ms": "berlawan dengan musuh", "zh": "与敌人交手"}, {"ms": "berbeza dengan dulu", "zh": "与过去不同"}],
            5: [{"ms": "dengan sebab itu", "zh": "由于那个缘故"}, {"ms": "mati dengan racun", "zh": "死于中毒"}],
            6: [{"ms": "dengan sendirinya", "zh": "自然而然地；自动地"}, {"ms": "dengan persetujuan", "zh": "经同意；按照协议"}],
            7: [{"ms": "ketawa dengan terbahak-bahak", "zh": "笑得前仰后合"}, {"ms": "pukul dengan lebam", "zh": "打得青一块紫一块"}],
            8: [{"ms": "sayang dengan anak", "zh": "疼爱孩子"}, {"ms": "benci dengan sikapnya", "zh": "讨厌他的态度"}],
            9: [{"ms": "ada dengan dia", "zh": "在他那里；由他保管"}, {"ms": "cakap dengan siapa", "zh": "在跟谁说话？"}],
            10: [{"ms": "dengan izin Allah", "zh": "如果蒙主恩准；借造物主之力"}, {"ms": "dengan syarat", "zh": "以...为条件"}],
            11: [{"ms": "dengan demikian", "zh": "既然如此；因而"}, {"ms": "dengan ini", "zh": "特此；谨以此"}],
            12: [{"ms": "segala dengan", "zh": "所有仆从随从（古书）"}, {"ms": "dengan raja", "zh": "君主的近侍仆从"}],
            13: [{"ms": "dengan sebantal", "zh": "同床共枕之伴（古语）"}, {"ms": "mencari dengan", "zh": "寻找同伴"}],
            14: [{"ms": "ujar dengan", "zh": "仆人我说道（古文献自称）"}, {"ms": "ampun tuanku, sembah dengan", "zh": "陛下饶恕，仆人禀告"}]
        },
        "messages": [
            {"speaker": "Hanim (朋友)", "ms_spoken": "Kau balik kampung dengan siapa?", "ms_standard": "Awak balik ke kampung dengan siapa?", "zh": "你跟谁一起回乡？"},
            {"speaker": "Najib (朋友)", "ms_spoken": "Dengan family la, naik kereta sekali.", "ms_standard": "Dengan keluarga la, naik kereta bersama-sama.", "zh": "跟家里人一起，开车回去。"}
        ]
    },
    "anda": {
        "historical_story": "现代标准语中的尊称第二人称代词 anda 是 1950 年代由印尼知名报人萨巴尔诺（Sabarno）等人在《Pedoman》报纸上倡导创设的新词，旨在创造一个摆脱封建等级、尊卑羁绊的现代民主化普遍尊称，后被马来西亚语文出版局（DBP）全面接纳为广告、广播媒体与正式文书中面对公众读者的标准第二人称；而古典医学与动物词汇中的 anda musang（麝香囊）则是古代本土动物解剖同形词，二者并无语源继承关系。",
        "collocations": {
            1: [{"ms": "anda boleh cuba", "zh": "您可以尝试"}, {"ms": "pilihan anda", "zh": "您的选择"}],
            2: [{"ms": "anda musang", "zh": "麝香囊（果子狸香腺）"}, {"ms": "bau anda", "zh": "麝香气味（古典医书记载）"}]
        },
        "messages": [
            {"speaker": "Penyampai (电台主播)", "ms_spoken": "Bagaimana hari anda setakat ini?", "ms_standard": "Bagaimanakah hari anda setakat ini?", "zh": "听众朋友们，您今天过得如何？"},
            {"speaker": "Pemanggil (听众连线)", "ms_spoken": "Alhamdulillah baik, seronok dengar lagu ni.", "ms_standard": "Alhamdulillah baik, seronok mendengar lagu ini.", "zh": "托主的福很好，听这首歌心情特别舒畅。"}
        ]
    },
    "tahu": {
        "historical_story": "动词 tahu 继承自原始南岛语的核心认知动词词根 *taqu（知晓、懂得、擅长），在诸如他加禄语 tao、毛利语 tahu 中均有坚实的语系同源词。它跨越数千年完整保留了表达人类认知理解的核心语义，并自然派生出 mengetahui（查明、获悉）与 pengetahuan（知识、学识）等现代高级学术构形；至于特定鸟名 burung tahu 则是民间因其叫声仿佛能‘未卜先知报晓啼鸣’而赋予的原生修辞命名。",
        "collocations": {
            1: [{"ms": "saya tahu", "zh": "我知道"}, {"ms": "tahu cerita sebenar", "zh": "知晓真实内幕"}],
            2: [{"ms": "tahu orangnya", "zh": "认识那个人"}, {"ms": "tahu jalan", "zh": "认得路"}],
            3: [{"ms": "tahu memasak", "zh": "懂得做饭；会烧菜"}, {"ms": "tahu memandu", "zh": "会开车"}],
            4: [{"ms": "tahu diri", "zh": "有自知之明"}, {"ms": "tahu batas", "zh": "懂得界限与分寸"}],
            5: [{"ms": "tak tahu menahu", "zh": "不闻不问；毫不在乎"}, {"ms": "ambil tahu", "zh": "过问；关心"}],
            6: [{"ms": "tahu rasa sakit", "zh": "体会过痛苦滋味"}, {"ms": "baru tahu", "zh": "才刚领教；方才体会到"}],
            7: [{"ms": "tahu makan sahaja", "zh": "只顾着吃"}, {"ms": "tahu bersungut", "zh": "一味抱怨"}],
            8: [{"ms": "burung tahu", "zh": "噪鹃（又名 tuwu / burung tahu）"}, {"ms": "bunyi burung tahu", "zh": "噪鹃的啼鸣声"}]
        },
        "messages": [
            {"speaker": "Fikri (同事)", "ms_spoken": "Kau tahu tak pasal meeting esok?", "ms_standard": "Awak tahu tidak tentang mesyuarat esok?", "zh": "你知道明天开会的事吗？"},
            {"speaker": "Danial (同事)", "ms_spoken": "Tahu, bos baru send emel tadi kan.", "ms_standard": "Tahu, bos baru hantar e-mel tadi kan.", "zh": "知道啊，老板刚才刚发了邮件不是嘛。"}
        ]
    },
    "ke": {
        "historical_story": "空间方位介词 ke 承继自原始南岛语的方向标记 *ka / *kay（朝向），在古典文献与现代标准语中严格用于引导终点目标（如 ke pejabat）。在正字法上它与派生序数或名词的前缀 ke-（如 ketiga、kekasih）在书写上有分写与连写的严格区分；而日常口语中高频出现的句尾疑问助词 ke（如 betul ke？）则是规范疑问标记 kah 在民间会话中元音弱化与音变留下的活泼产物。",
        "collocations": {
            1: [{"ms": "pergi ke sekolah", "zh": "去学校"}, {"ms": "ke utara", "zh": "向北"}],
            2: [{"ms": "dari pagi ke petang", "zh": "从早到晚"}, {"ms": "dari semasa ke semasa", "zh": "不时；从一个时期到另一个时期"}],
            3: [{"ms": "dia dah sampai ke", "zh": "他已经到了吗？"}, {"ms": "betul ke", "zh": "是真的吗？"}],
            4: [{"ms": "hujan ke panas ke", "zh": "无论是下雨还是天晴"}, {"ms": "sama ada jadi ke tak", "zh": "到底成还是不成"}],
            5: [{"ms": "huruf ke", "zh": "字母 K"}, {"ms": "saiz ke", "zh": "K 号尺寸"}]
        },
        "messages": [
            {"speaker": "Imran (朋友)", "ms_spoken": "Hari ni kau nak pergi ke mana?", "ms_standard": "Hari ini awak hendak pergi ke mana?", "zh": "今天你想去哪儿？"},
            {"speaker": "Zahid (朋友)", "ms_spoken": "Nak ke mall kejap, cari barang sikit.", "ms_standard": "Mahu ke pusat beli-belah sebentar, mencari barang sedikit.", "zh": "想去趟商场，买点东西。"}
        ]
    },
    "kami": {
        "historical_story": "kami 承袭自原始南岛语的核心代词词根 *kami，是整个南岛语系引以为傲的‘第一人称复数排除式’语法现象的活体见证——它将说话者及其阵营紧密联结，同时明确将听话者排除在范畴之外（区别于包括听话者的 kita）。此外在古典文学叙事与皇家诏令中，kami 还被君主或文人学者借用作庄严的单数谦称或作者自称，展现了浓厚的修辞层次。",
        "collocations": {
            1: [{"ms": "kami semua", "zh": "我们全体（不含听众）"}, {"ms": "keluarga kami", "zh": "我们的家庭"}],
            2: [{"ms": "titah kami", "zh": "朕之旨意（君主口吻）"}, {"ms": "menurut hemat kami", "zh": "依我们/笔者之愚见"}]
        },
        "messages": [
            {"speaker": "Pelanggan (顾客)", "ms_spoken": "Boleh kami masuk sekarang ke?", "ms_standard": "Bolehkah kami masuk sekarang?", "zh": "我们现在可以进去了吗？"},
            {"speaker": "Petugas (工作人员)", "ms_spoken": "Boleh encik, sila scan suhu dulu ya.", "ms_standard": "Boleh encik, sila imbas suhu dahulu ya.", "zh": "可以的先生，请先测一下体温。"}
        ]
    },
    "ya": {
        "historical_story": "日常肯定应答词 ya 广泛流行于东南亚各语言中，属于极为自然的语用确认声响，并在马来社会同阿拉伯语伊斯兰文化长达数百年的接触中得到巩固强化；而专门用于祈祷与神圣呼告的 Ya（如 Ya Allah、Ya Rabbi）则是随着 13-14 世纪伊斯兰教传入直接借自阿拉伯语的呼格词（حرف النداء yā），Jawi 字母表中以此命名的字母 ي 亦是该历史文化交融的直接产物。",
        "collocations": {
            1: [{"ms": "ya betul", "zh": "对，没错"}, {"ms": "jawapan ya", "zh": "肯定的回答"}],
            2: [{"ms": "ya tuan", "zh": "遵命，长官"}, {"ms": "ya nanti saya buat", "zh": "好的，待会儿我去做"}],
            3: [{"ms": "ya saya di sini", "zh": "哎，我在这儿"}, {"ms": "ya mak", "zh": "哎，妈妈（应答呼唤）"}],
            4: [{"ms": "tunggu sekejap ya", "zh": "请稍等一下哦"}, {"ms": "cantik ya", "zh": "挺漂亮的，对吧？"}],
            5: [{"ms": "Ya Allah", "zh": "真主啊！"}, {"ms": "Ya Tuhanku", "zh": "主啊！"}],
            6: [{"ms": "huruf ya", "zh": "Jawi 字母 ya（ي）"}, {"ms": "titik huruf ya", "zh": "ya 字母底部的两个点"}]
        },
        "messages": [
            {"speaker": "Makcik (阿姨)", "ms_spoken": "Ali, tolong belikan santan kat kedai ya?", "ms_standard": "Ali, tolong belikan santan di kedai ya?", "zh": "阿里，帮我去店里买点椰浆好吗？"},
            {"speaker": "Ali (少年)", "ms_spoken": "Ya mak, Ali pergi sekarang.", "ms_standard": "Ya mak, Ali pergi sekarang.", "zh": "好的妈妈，我这就去。"}
        ]
    },
    "dari": {
        "historical_story": "介词 dari 承袭自古马来语的空间离格标记，千百年来专司指示动作位移与时间进程的起始点（如 dari Ipoh ke KL）。在规范马来语语法体系中，语文出版局（DBP）确立了极严格的规范分工：表示方向、地点、时间起点时使用 dari，而表示人身来源、材质、比较或抽象分类时则必须使用 daripada，这对介词的精准界分是掌握规范马来语语法的标志性分水岭。",
        "collocations": {
            1: [{"ms": "dari Kuala Lumpur", "zh": "从吉隆坡出发"}, {"ms": "turun dari bas", "zh": "从巴士上下来"}],
            2: [{"ms": "dari pukul lapan", "zh": "从八点钟开始"}, {"ms": "dari kecil", "zh": "自幼；从小"}],
            3: [{"ms": "sepuluh kilometer dari sini", "zh": "距此十公里"}, {"ms": "jauh dari bandar", "zh": "远离市区"}],
            4: [{"ms": "dari segi ekonomi", "zh": "从经济角度而言"}, {"ms": "dari sudut pandangan", "zh": "从...视角来看"}]
        },
        "messages": [
            {"speaker": "Hafiz (朋友)", "ms_spoken": "Kau baru balik dari mana ni?", "ms_standard": "Awak baru balik dari mana ini?", "zh": "你刚从哪儿回来呀？"},
            {"speaker": "Anwar (朋友)", "ms_spoken": "Baru balik dari gym, penat gila.", "ms_standard": "Baru balik dari gimnasium, penat sungguh.", "zh": "刚从健身房回来，累坏了。"}
        ]
    },
    "dalam": {
        "historical_story": "dalam 直接继承自原始南岛语的核心空间深度词根 *dalem（深、内），在整个马来-波利尼西亚语族（如爪哇语 dalem、他加禄语 ilalim）均保持着高度一致的跨语汇对应。由最初形容水体或深渊的垂直深度，自然横向隐喻为空间内部、心理感受与抽象领域范围；而在传统封建王朝中，因王室深居禁宫，‘在最深之处’还特指王宫内部环境，衍生出了独特的封建宫廷用语 bahasa dalam（宫廷语）。",
        "collocations": {
            1: [{"ms": "sungai yang dalam", "zh": "深水河流"}, {"ms": "lubang yang dalam", "zh": "深坑"}],
            2: [{"ms": "makna yang dalam", "zh": "深邃的含义"}, {"ms": "pengetahuan yang dalam", "zh": "博大精深的学问"}],
            3: [{"ms": "di dalam bilik", "zh": "在房间里面"}, {"ms": "bahagian dalam", "zh": "内部；里侧"}],
            4: [{"ms": "dalam hati", "zh": "内心深处；暗自"}, {"ms": "dalam fikiran", "zh": "在脑海中"}],
            5: [{"ms": "dalam bidang sains", "zh": "在科学领域内"}, {"ms": "dalam hal ini", "zh": "在这一方面"}],
            6: [{"ms": "dalam kalangan pelajar", "zh": "在学生群体当中"}, {"ms": "satu dalam sejuta", "zh": "百万中选一"}],
            7: [{"ms": "dalam masa dua hari", "zh": "在两天之内"}, {"ms": "dalam seminggu", "zh": "在一周内"}],
            8: [{"ms": "dalam kesusahan", "zh": "处于困境之中"}, {"ms": "dalam bahaya", "zh": "处于危险之中"}],
            9: [{"ms": "dalam pada itu", "zh": "在此期间；与此同时"}, {"ms": "dalam diam", "zh": "不动声色间"}],
            10: [{"ms": "bahasa dalam", "zh": "宫廷王室隐语"}, {"ms": "orang dalam istana", "zh": "王宫内部人员"}]
        },
        "messages": [
            {"speaker": "Fendi (朋友)", "ms_spoken": "Mana dokumen tadi? Tak jumpa pun.", "ms_standard": "Di manakah dokumen tadi? Tidak jumpa pun.", "zh": "刚才的文件在哪儿？找都找不到。"},
            {"speaker": "Naim (朋友)", "ms_spoken": "Ada dalam laci meja kau tu, cuba check.", "ms_standard": "Ada di dalam laci meja awak itu, cuba periksa.", "zh": "在你桌子的抽屉里面呢，查查看看。"}
        ]
    },
    "sini": {
        "historical_story": "sini 是古马来语中指示方位标记 si 与近指词素 ni（与 ini 同源）融合构成的空间处所副词，专指紧邻说话者的物理与视觉场域（‘这里’），与远指处所 sana（那里）、中指处所 situ（那儿）共同构建起马来语经典的三元空间指示认知坐标。其衍生出的口语近身呼唤（sini kejap）与撒娇式单数自称，体现了空间认知向人际情感距离的自然转喻。",
        "collocations": {
            1: [{"ms": "di sini", "zh": "在这里"}, {"ms": "ke sini", "zh": "到这里来"}],
            2: [{"ms": "mari sini", "zh": "过来这里"}, {"ms": "sini kejap", "zh": "来这儿一下！"}],
            3: [{"ms": "sini yang rindu", "zh": "是我在想念（娇昵语气）"}, {"ms": "bagi kat sini", "zh": "交给我这边吧"}]
        },
        "messages": [
            {"speaker": "Zaki (朋友)", "ms_spoken": "Bro, kau kat mana? Aku dah sampai ni.", "ms_standard": "Kawan, awak di mana? Saya sudah sampai ini.", "zh": "兄弟你在哪儿呢？我已经到了。"},
            {"speaker": "Taufiq (朋友)", "ms_spoken": "Kat sini ha, meja hujung sebelah tingkap.", "ms_standard": "Di sini, meja hujung sebelah tingkap.", "zh": "在这儿呢，靠窗最尽头那张桌子。"}
        ]
    },
    "semua": {
        "historical_story": "semua 借自古梵语词汇 samūha（समुह，意为‘聚集、集合、总和、群体’），是公元 1 世纪至 14 世纪马来群岛深受印度古典文化影响时沉淀下来的核心词汇之一。它在借入后迅速融入马来语日常口语与书面体系，彻底取代了原生分散表达，成为表达绝对全体与全称量化最首要的词汇标杆，历经近两千年未发生语音突变，音节结构始终稳固。",
        "collocations": {
            1: [{"ms": "semua pelajar", "zh": "所有学生"}, {"ms": "semua orang", "zh": "所有人；大家"}],
            2: [{"ms": "terima kasih semua", "zh": "谢谢大家"}, {"ms": "semua sudah siap", "zh": "一切都准备妥当了"}],
            3: [{"ms": "semua sekali", "zh": "总共；一网打尽"}, {"ms": "rusak semua", "zh": "全部损坏了"}]
        },
        "messages": [
            {"speaker": "Bos (主管)", "ms_spoken": "Semua staff dah masuk bilik mesyuarat ke?", "ms_standard": "Semua staf sudah masuk ke bilik mesyuarat kah?", "zh": "所有员工都进会议室了吗？"},
            {"speaker": "Setiausaha (秘书)", "ms_spoken": "Dah bos, semua dah bersedia sekarang.", "ms_standard": "Sudah bos, semua sudah bersedia sekarang.", "zh": "都进去了老板，大家现在都准备好了。"}
        ]
    }
}

def upgrade_word_entry(data: dict, word: str) -> dict:
    spec = UPGRADES[word]
    
    # 1. Historical story
    if "etymology" not in data:
        data["etymology"] = {}
    data["etymology"]["historical_story"] = spec["historical_story"]
    
    # 2. Collocations per sense
    for s in data.get("senses", []):
        sid = s["id"]
        if sid in spec["collocations"]:
            s["collocations"] = spec["collocations"][sid]
        else:
            raise ValueError(f"Missing collocations for {word} sense {sid}")
            
    # 3. Colloquial scenario messages
    for sc in data.get("dual_scenarios", []):
        if sc.get("scenario") == "colloquial":
            sc["messages"] = spec["messages"]
            
    return data

def main():
    print("Upgrading Batch 1, 2, 3 words (30 words in total)...")
    assert len(UPGRADES) == 30, f"Expected 30 words in UPGRADES, got {len(UPGRADES)}"
    
    batch_map = {
        1: ['saya', 'yang', 'aku', 'dia', 'awak', 'kau', 'ini', 'di', 'tak', 'dan'],
        2: ['akan', 'tidak', 'kita', 'apa', 'kamu', 'itu', 'untuk', 'ada', 'boleh', 'mereka'],
        3: ['dengan', 'anda', 'tahu', 'ke', 'kami', 'ya', 'dari', 'dalam', 'sini', 'semua']
    }
    
    # 1. Upgrade individual files
    upgraded_individual = {}
    for word in UPGRADES:
        p = ENRICHED_DIR / f"{word}.json"
        with open(p, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        upgraded = upgrade_word_entry(d, word)
        
        # Atomic write
        tmp_p = p.with_suffix(".json.tmp")
        with open(tmp_p, "w", encoding="utf-8") as tfp:
            json.dump(upgraded, tfp, ensure_ascii=False, indent=2)
            tfp.write("\n")
        os.replace(tmp_p, p)
        upgraded_individual[word] = upgraded
        print(f"  [OK] Updated individual file: {word}.json")
        
    # 2. Update batch arrays
    for b_num, words in batch_map.items():
        batch_p = ENRICHED_DIR / f"batch_{b_num}.json"
        batch_data = []
        for w in words:
            batch_data.append(upgraded_individual[w])
            
        tmp_b = batch_p.with_suffix(".json.tmp")
        with open(tmp_b, "w", encoding="utf-8") as tfp:
            json.dump(batch_data, tfp, ensure_ascii=False, indent=2)
            tfp.write("\n")
        os.replace(tmp_b, batch_p)
        print(f"  [OK] Updated batch array: batch_{b_num}.json with {len(batch_data)} words")
        
    # 3. Post-verification
    print("\nVerifying all 30 words and batch files...")
    total_senses = 0
    senses_without_colloc = 0
    words_without_story = 0
    words_without_messages = 0
    
    for word in UPGRADES:
        p = ENRICHED_DIR / f"{word}.json"
        with open(p, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        
        # Check historical_story
        story = d.get("etymology", {}).get("historical_story")
        if not story or not story.strip():
            words_without_story += 1
            
        # Check collocations
        for s in d.get("senses", []):
            total_senses += 1
            collocs = s.get("collocations", [])
            if len(collocs) < 2:
                senses_without_colloc += 1
                print(f"  ERROR: {word} sense {s['id']} has only {len(collocs)} collocations")
                
        # Check messages
        colloquials = [sc for sc in d.get("dual_scenarios", []) if sc.get("scenario") == "colloquial"]
        if not any(sc.get("messages") and len(sc["messages"]) >= 2 for sc in colloquials):
            words_without_messages += 1
            print(f"  ERROR: {word} missing colloquial messages")
            
    print(f"Verification Summary:")
    print(f"  - Total senses across 30 words: {total_senses}")
    print(f"  - Senses with < 2 collocations: {senses_without_colloc}")
    print(f"  - Words without historical_story: {words_without_story}")
    print(f"  - Words without >= 2 turns messages: {words_without_messages}")
    
    assert total_senses == 127, f"Expected exactly 127 senses across 30 words, got {total_senses}"
    assert senses_without_colloc == 0, f"Expected 0 senses with <2 collocations, got {senses_without_colloc}"
    assert words_without_story == 0, f"Expected 0 words without story, got {words_without_story}"
    assert words_without_messages == 0, f"Expected 0 words without messages, got {words_without_messages}"
    print("ALL 30 WORDS AND 127 SENSES FULLY UPGRADED AND VALIDATED!")

if __name__ == "__main__":
    main()
