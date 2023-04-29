def print_cards(cards):
    for i in range(len(cards)):
        if i != 0 and cards[i] != cards[i - 1]:
            print(' ', end='')
        print(cards[i], end='')


def main_interface(users_name, tag, users_score, users_cards_len,
                   played_cards, user, now_score, now_user, head_master):
    print(f'\n\n当前场上分数：{now_score}')

    # 输出其它玩家
    i = (tag + 1) % 6
    while i != tag:
        if i % 2 != tag % 2:
            print('      {0:<20}{1:>4}张{2:>5}分'.format(users_name[i], users_cards_len[i], users_score[i]), end='')
        else:
            print('(Team){0:<20}{1:>4}张{2:>5}分'.format(users_name[i], users_cards_len[i], users_score[i]), end='')

        if i == head_master:
            print('{0:^6}'.format('头科'), end='')
        else:
            print('      ', end='')

        if i == now_user:
            print('<<<NOW ROUND<<<', end='')

        if len(played_cards[i]) != 0:
            print_cards(played_cards[i])

        i = (i + 1) % 6
        print()

    # 输出自己
    print('------------------------\n')
    print('(Team){0:<20}{1:>4}张{2:>5}分'.format(user.name, len(user.cards), user.score), end='')

    if tag == head_master:
        print('{0:^6}'.format('头科'), end='')
    else:
        print('      ', end='')

    if tag == now_user:
        print('<<<NOW ROUND<<<', end='')

    if len(user.played_card) != 0:
        print_cards(user.played_card)

    print('\n')
    print('                                     ', end='')
    print_cards(user.cards)
    print()


def game_over_interface(tag, _if_game_over):
    print('\n')
    if tag % 2 + 1 == (_if_game_over + 2) % 2:
        print('游戏结束，你的队伍获得了胜利', end='')
        if _if_game_over < 0:
            print('，并成功双统')
    else:
        print('游戏结束，你的队伍未能取得胜利', end='')
        if _if_game_over < 0:
            print('，并被对方双统')
