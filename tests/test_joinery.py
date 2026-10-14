import unittest
from vandesign.core.joinery import DadoShelf

class JoineryRegression(unittest.TestCase):
    def test_dado_6(self):
        s = DadoShelf(1200, 18, 6, 0.3)
        self.assertAlmostEqual(s.shelf_length_mm, 1175.4)
        self.assertAlmostEqual(s.insertion_each_end_mm, 5.7)

    def test_dado_10(self):
        s = DadoShelf(1200, 18, 10, 0.3)
        self.assertAlmostEqual(s.shelf_length_mm, 1183.4)
        self.assertAlmostEqual(s.shelf_start_x_mm, 8.3)

    def test_resize(self):
        self.assertAlmostEqual(DadoShelf(1000, 18, 10, 0.3).shelf_length_mm, 983.4)

    def test_material(self):
        self.assertAlmostEqual(DadoShelf(1200, 15, 10, 0.3).shelf_length_mm, 1189.4)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            DadoShelf(1000, 18, 18, 0.3)
