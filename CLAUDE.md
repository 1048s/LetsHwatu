# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- **Run Server**: `python server/server.py` (defaults to host `0.0.0.0`, port `9999`)
- **Run Client**: `python client/client.py` (defaults to connecting to `127.0.0.1:9999`)

## Architecture & Structure

This repository contains a multiplayer Hwatu (Go-Stop/Matgo) card game implemented in Python using standard sockets and Tkinter.

- **`server/server.py` (Server)**:
  - **Authoritative Game Engine**: Manages rooms, turn states, card deck shuffling, dealing, matching rules, and score calculation (`calculate_score`, `RoomGame`).
  - **Networking**: Multithreaded TCP server (`Server`, `ClientHandler`) using line-delimited JSON messages (`json.dumps`/`json.loads` separated by `\n`).
  - **Rooms**: Supports 2-player rooms identified by 4-letter uppercase codes.

- **`client/client.py` (Client)**:
  - **GUI**: Built with Tkinter (`GameApp`), featuring a lobby for room creation/joining and a game board view displaying opponent status, shared table cards, user hands, and collected cards.
  - **Networking**: Connects to the server via TCP socket in a background thread (`recv_loop`) and dispatches messages to the main Tkinter thread using `root.after()`.
