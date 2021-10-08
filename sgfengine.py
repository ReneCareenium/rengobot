# Needs sgf-render and sgfmill
# https://mjw.woodcraft.me.uk/sgfmill/doc/1.1.1/properties.html?highlight=list%20properties
import os
from sgfmill import sgf, boards, sgf_moves, ascii_boards

# This file only deals with the png and sgf side of things. To manage users etc go to the main file.

def new_game(channel_id, handicap=0, komi=6.5):
    game= sgf.Sgf_game(19)
    game.root.set("KM", komi)
    if handicap>=2:
        game.root.set("HA", handicap)

        handicap_dict={
                2: [(3,3), (15,15)],
                3: [(3,3), (15,15), (15,3)],
                4: [(3,3), (15,15), (15,3), (3,15)],
                5: [(3,3), (15,15), (15,3), (3,15), (9,9)],
                6: [(3,3), (15,15), (15,3), (3,15), (9,3), (9,15)],
                7: [(3,3), (15,15), (15,3), (3,15), (9,3), (9,15), (9,9)],
                8: [(3,3), (15,15), (15,3), (3,15), (9,3), (9,15), (3,9), (15,9)],
                9: [(3,3), (15,15), (15,3), (3,15), (9,3), (9,15), (3,9), (15,9), (9,9)]}
        game.root.set("AB",handicap_dict[handicap])

    with open (channel_id+".sgf", "wb") as f:
        f.write(game.serialise())
    f.close()

    os.system("sgf-render --style fancy --label-sides nesw -o "+channel_id+".png -n last "+channel_id+".sgf")

#0 if black to play, 1 if white to play
def next_colour(channel_id):
    with open(channel_id+".sgf","rb") as f:
        game = sgf.Sgf_game.from_bytes(f.read())
    f.close()

    node= game.get_last_node()
    return 1 if ("B" in node.properties() or "AB" in node.properties()) else 0

# Could be an illegal move, or maybe I don't understand the message
# outputs to <channel_id>.png
def play_move(channel_id, messagestr, player, overwrite=False):

    thecol= ord(messagestr[0].lower()) - ord('a')
    if thecol>8: thecol-=1 # Go boards don't have an I column!!
    therow= int(messagestr[1:]) - 1

    with open(channel_id+".sgf","rb") as f:
        game = sgf.Sgf_game.from_bytes(f.read())
    f.close()

    koban=None
    node= game.get_last_node()
    board, moves= sgf_moves.get_setup_and_moves(game)
    if overwrite:
        node2= node.parent
        node.delete()
        node= node2
        moves= moves[:-1]

    for (colour, (row, col)) in moves:
        koban=board.play(row,col,colour)

    if (therow, thecol)==koban:
        raise ValueError("Ko banned move!")

    colour = "w" if ("B" in node.properties() or "AB" in node.properties()) else "b"

    board2= board.copy()
    try:
        koban2=board2.play(therow, thecol, colour)
    except ValueError as e:
        raise ValueError("Illegal move! There is a stone there.")

    if board2.get(therow,thecol) == None:
        raise ValueError("Illegal move! No self-captures allowed.")

    node2= node.new_child()
    node2.set(("B" if colour =='b' else "W"), (therow,thecol))
    if koban2 is not None: node2.set("SQ", [koban2])
    node2.set("CR", [(therow, thecol)])
    node2.set("C", player) # I think this would be fun for the review
    if node.has_property("CR"): node.unset("CR")
    if node.has_property("SQ"): node.unset("SQ")

    with open (channel_id+".sgf", "wb") as f:
        f.write(game.serialise())
    f.close()

    os.system("sgf-render --style fancy -o "+channel_id+".png -n last "+channel_id+".sgf")

# colour is "B" if black resigns, "W" if white resigns
def resign(channel_id, colour, file_name):
    with open(channel_id+".sgf","rb") as f:
        game = sgf.Sgf_game.from_bytes(f.read())
    f.close()

    node= game.root
    node.set("RE", ("B" if colour=="W" else "W")+"+R")

    with open (file_name, "wb") as f:
        f.write(game.serialise())
    f.close()

    os.remove(channel_id+".sgf")
