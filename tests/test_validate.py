import pytest

from ct_monitor.validate import normalize_domain

LABEL_63 = "a" * 63
LABEL_64 = "a" * 64
# 63 + 1 + 63 + 1 + 63 + 1 + 61 = 253 文字
DOMAIN_253 = ".".join([LABEL_63, LABEL_63, LABEL_63, "a" * 61])
# 63 + 1 + 63 + 1 + 63 + 1 + 62 = 254 文字
DOMAIN_254 = ".".join([LABEL_63, LABEL_63, LABEL_63, "a" * 62])


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # すでに正規形のドメインはそのまま返る
        ("example.com", "example.com"),
        # DNS は大文字小文字を区別しないので小文字に揃える
        ("Example.COM", "example.com"),
        # ワイルドカード証明書の先頭 *. は取り除いて基底ドメインにする
        ("*.example.com", "example.com"),
        # FQDN 表記の末尾 . は取り除く
        ("example.com.", "example.com"),
        # xn-- で始まるラベル（Punycode）はそのまま受け入れる
        ("xn--bcher-kva.example", "xn--bcher-kva.example"),
        # ラベル長 63 文字は上限ちょうどなので受け入れる
        (f"{LABEL_63}.com", f"{LABEL_63}.com"),
        # 全体 253 文字は上限ちょうどなので受け入れる
        (DOMAIN_253, DOMAIN_253),
        # 末尾 . を除いた長さで判定するので、253 文字 + 末尾 . も受け入れる
        (DOMAIN_253 + ".", DOMAIN_253),
        # *. 除去・小文字化・末尾 . 除去が重なっても正規形になる
        ("*.Example.COM.", "example.com"),
    ],
)
def test_accepts_and_normalizes(raw, expected):
    assert normalize_domain(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        # 空文字はドメイン名ではない
        "",
        # ドット区切りのない単一ラベルは公開ドメインではない
        "localhost",
        # ラベルの先頭がハイフンなのは不正
        "-example.com",
        # ラベルは 63 文字まで。64 文字は不正
        f"{LABEL_64}.com",
        # 全体は 253 文字まで。254 文字以上は不正
        DOMAIN_254,
        # アンダースコアはホスト名に使えない文字
        "exa_mple.com",
        # IP アドレスはドメイン名ではない
        "192.0.2.1",
        # メールアドレス形式は @ を含み不正
        "user@example.com",
        # 先頭の *. は 1 つだけ許される。2 つ目以降は不正
        "*.*.example.com",
        # ワークフローコマンド注入に使われる形式は捨てる
        "::error::test",
        # 改行を含む値は別ドメインの混入や注入に使えるので捨てる
        "example.com\nevil.com",
        # 末尾だけの改行でも、$ が改行直前に一致する実装をすり抜けるので捨てる
        "example.com\n",
        # ASCII 以外の文字は Punycode 化されていない限り不正
        "exämple.com",
        # ケルビン記号 (U+212A) は小文字化すると ASCII の k になるため、正規化前に弾く
        "testK.com",
        # 空ラベル（連続するドット）は不正
        "example..com",
        # 先頭のドットは空ラベルになるので不正
        ".example.com",
        # ラベルの末尾がハイフンなのは不正
        "example-.com",
    ],
)
def test_rejects_invalid(raw):
    assert normalize_domain(raw) is None
