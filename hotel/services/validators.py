def pos_int(value,minimum=1):
    try: v=int(value)
    except (ValueError,TypeError): raise ValueError('Vui lòng nhập một số nguyên hợp lệ.')
    if v<minimum:raise ValueError(f'Giá trị tối thiểu là {minimum}.')
    return v
