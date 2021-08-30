# Needs sgf-render and sgfmill
# https://mjw.woodcraft.me.uk/sgfmill/doc/1.1.1/properties.html?highlight=list%20properties
import os
from sgfmill import sgf, boards, sgf_moves, ascii_boards

# This file only deals with the png and sgf side of things. To manage users etc go to the main file.

def new_game(channel_id):
    game= sgf.Sgf_game(19)

    with open (channel_id+".sgf", "wb") as f:
        f.write(game.serialise())
    f.close()

    os.system("sgf-render --style fancy -o "+channel_id+".png -n last "+channel_id+".sgf")

# Could be an illegal move, or maybe I don't understand the message
# outputs to <channel_id>.png
def play_move(channel_id, messagestr, player):

    thecol= ord(messagestr[0].lower()) - ord('a')
    if thecol>8: thecol-=1 # Go boards don't have an I column!!
    therow= int(messagestr[1:]) - 1

    with open(channel_id+".sgf","rb") as f:
        game = sgf.Sgf_game.from_bytes(f.read())
    f.close()

    koban=None
    node= game.get_last_node()
    board, moves= sgf_moves.get_setup_and_moves(game)
    for (colour, (row, col)) in moves:
        koban=board.play(row,col,colour)

    if (therow, thecol)==koban:
        raise ValueError("Ko banned move!")

    colour = "w" if ("B" in node.properties()) else "b"

    board2= board.copy()
    try:
        board2.play(therow, thecol, colour)
    except ValueError as e:
        raise ValueError("Illegal move1!")

    if ascii_boards.render_board(board)== ascii_boards.render_board(board2):
        raise ValueError("Illegal move2!")

    #print(moves)

    node2= node.new_child()
    node2.set(("B" if colour =='b' else "W"), (therow,thecol))
    if koban is not None: node2.set("SQ", [koban])
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
