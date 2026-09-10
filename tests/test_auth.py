from auth import hash_password, verify_password, new_session_token, new_readable_password


def test_verify_password_correct():
    digest, salt = hash_password("hunter2")
    assert verify_password("hunter2", salt, digest) is True


def test_verify_password_wrong():
    digest, salt = hash_password("hunter2")
    assert verify_password("wrong", salt, digest) is False


def test_same_password_different_salt_gives_different_hash():
    digest1, salt1 = hash_password("hunter2")
    digest2, salt2 = hash_password("hunter2")
    assert salt1 != salt2
    assert digest1 != digest2


def test_session_token_is_unique():
    assert new_session_token() != new_session_token()


def test_readable_password_is_all_digits_length_8():
    pw = new_readable_password()
    assert len(pw) == 8
    assert pw.isdigit()
