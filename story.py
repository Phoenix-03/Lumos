class Story:
    def __init__(self):
        self.scenes = {
            'start': {
                'text': 'You have received a message: "Congratulations! You have received your monthly income of ₹1,00,000."',
                'image': 'income.png',
                'background': 'home.jpeg',
                'choices': {
                    's2': 'Lesssgoooo!',
                    's2': 'Yayyyyy!'
                }
            },
            's2': {
                'text': 'Your laptop broke down! Your technician suggested you to buy a new best performance laptop which is worth Rs. 70,000. The PlayStation you were waiting for, recently launched. It costs Rs.50,000.',
                'image': 'laptop.png',
                'img': 'play.jpeg',
                'background': 'shop.jpeg',
                'choices': {
                    's4': 'Buy the Rs. 70,000 laptop',
                    's3': 'Buy a low quality laptop at Rs. 35,000 and the Playstation'
                }
            },
            's3': {
                'text': 'You realise that your new laptop is not apt for your work.You decide to invest and try to gain profits.',
                'image': 'spend.jpg',
                'background': 'background_spend_money.jpg',
                'choices': {
                    's6': 'Click on link given in a message that you got earlier claiming that you will receive 2 lakhs after investing 50k in a said government scheme.',
                    's5': 'Invest in stocks'
                }
            },
            's4': {
                'text': 'You have a great laptop! You even got a Rs. 10,000 discount. You have now settled in your new work place and decide to move out of your parent\'s house and get yourself a new home.',
                'background': 'newhome.jpeg',
                'choices': {
                    's5': 'Buy a new flat',
                    's6': 'Rent a flat'
                }
            },
            's5': {
                'text': 'The news says /" /" Do you wish to analyse and invest by yourself or go for mutual funds?',
                'image': 'house.jpg',
                'background': 'background_house.jpg',
                'choices': {
                    's8': 'Anaylse by yourself',
                    's9': 'Mutual Funds'
                }
            },
        }

    def get_scene(self, scene_name):
        return self.scenes.get(scene_name, self.scenes['start'])

story = Story()
