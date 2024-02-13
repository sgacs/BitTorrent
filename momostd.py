#!/usr/bin/python

# This is a slightly smarter version of the dummy peer.
# The setup script will copy it to create the versions you edit

import logging
import random

from messages import Request, Upload
from peer import Peer
from util import even_split


class MomoStd(Peer):
    def post_init(self):
        print("post_init(): %s here!" % self.id)

        # Declare any variables here that you want to be able to access in future rounds
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
        self.frequencies = {}
        self.pieces = []
        self.conf = None
        self.max_requests = 0
        self.blocks_per_piece = 0
        self.available_pieces = set()
        self.downloads = []
        self.uploaded = 0
        self.downloaded = 0
        self.requests_sent = []
        self.uploads_received = []
        self.choked_by = set()
        self.interested_in = set()
        self.optimistic_unchoked = None
        self.round = 0

    def requests(self, peers, history):
        """
        peers: available info about the peers (who has what pieces)
        history: what's happened so far as far as this peer can see

        returns: a list of Request() objects

        This will be called after update_pieces() with the most recent state.
        """

        # Calculate the pieces you still need
        needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
        needed_pieces = list(filter(needed, list(range(len(self.pieces)))))
        # Symmetry breaking is good, it creates more opportunities to trade
        # Try commenting this out and see what happens to performance...
        random.shuffle(needed_pieces)

        np_set = set(needed_pieces)  # sets support fast intersection ops.

        logging.debug("%s here: still need pieces %s" % (self.id, needed_pieces))

        requests = []  # We'll put all the things we want here

        # count frequencies of all pieces that the other peers have
        # this will be useful for implementing rarest first
        ###########################################################
        # We added this                                           #
        ###########################################################
        frequencies = {}
        for peer in peers:
            for piece in peer.available_pieces:
                if piece in frequencies:
                    frequencies[piece] = frequencies[piece] + 1
                else:
                    frequencies[piece] = 1

        # request all available pieces from all peers!
        # (up to self.max_requests from each)
        #############################################################################
        # We adapted this code from dummy to implement rarest first                 #
        #############################################################################
        for peer in peers:
            av_set = set(peer.available_pieces)
            isect = av_set.intersection(np_set)
            n = int(min(self.max_requests, len(isect)))
            # More symmetry breaking -- ask for random pieces when tied.
            isectlist = list(isect)
            random.shuffle(isectlist)
            isectlist.sort(key=lambda p: frequencies[p])
            for piece_id in isectlist[:n]:
                # aha! The peer has this piece! Request it.
                start_block = self.pieces[piece_id]
                r = Request(self.id, peer.id, piece_id, start_block)
                requests.append(r)

        return requests

    def uploads(self, requests, peers, history):
        round = history.current_round()
        logging.debug("%s again. It's round %d." % (self.id, round))

        # Initial setup for no requests scenario
        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
        else:
            # Standard strategy for choosing whom to unchoke
            # logging.debug(
            #    "Still here: %s, uploading to a random peer %d" % self.id, chosen
            # )
            chosen = [
                req.requester_id
                for req in random.sample(requests, min(len(requests), 3))
            ]  # Example: unchoke up to 3 peers based on your strategy
            bws = even_split(self.up_bw, len(chosen))

            # Optimistic unchoking every N rounds
            unchoke_int = 3  # For example, every 3 rounds
            if round % unchoke_int == 0:
                # Ensure not to optimistically unchoke an already chosen peer
                available_peers = {
                    req.requester_id
                    for req in requests
                    if req.requester_id not in chosen
                }
                if available_peers:
                    optimistic_unchoke_peer = random.choice(list(available_peers))
                    chosen.append(optimistic_unchoke_peer)
                    # Adjust bandwidths after adding an optimistically unchoked peer
                    bws = even_split(self.up_bw, len(chosen))

        uploads = [Upload(self.id, peer_id, bw) for (peer_id, bw) in zip(chosen, bws)]
        return uploads
