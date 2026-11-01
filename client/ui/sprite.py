import tkinter as tk

class SpriteManager:
    def __init__(self, path):
        self.img = tk.PhotoImage(file=path)
        self.cw = self.img.width() // 8
        self.ch = self.img.height() // 6
        self.cache = {}

    def get_card_image(self, card_data):
        # Determine index 0-47
        month = card_data['month'] - 1
        ctype = card_data['ctype']
        type_order = {'광': 0, '열끗': 1, '띠': 2, '피': 3}[ctype]

        # Standard Hwatu mapping usually follows month-order
        idx = month * 4 + type_order

        if idx not in self.cache:
            col = idx % 8
            row = idx // 8
            # Create a temporary PhotoImage to hold the crop
            # Note: master=tk._default_root is often needed in threads or complex layouts
            subimg = tk.PhotoImage()
            # Crop using tk 'copy'
            subimg.tk.call(subimg, 'copy', self.img,
                          '-from', col*self.cw, row*self.ch, (col+1)*self.cw, (row+1)*self.ch,
                          '-to', 0, 0)

            # Subsample to fit compact window (~1/4 size)
            resized = subimg.subsample(4, 4)
            self.cache[idx] = resized
        return self.cache[idx]
