-- JUNCTION / stagedemo3 「見たものが、そうなる」
-- ★このファイルが編集元。assets/components/Liminal.lua は gen_liminal.py が書き出す複製。
--
-- 仕組みはひとつだけ:
--   建物の破片は、焦点 F から見たときだけ【本物と同じ形に重なる】ように置いてある
--   (F 中心の相似変換 P' = F + k(P-F))。プレイヤーの目がその位置へ来ると、対応点への
--   視線の角度差が 0 に近づく。lock 度未満まで詰めて【見て】いれば、破片は本物になる。
-- ★押すボタンは無い。歩いて、見る。それだけ。
-- ★画面に文字を出さない。合い具合は中央の環・継ぎ目の光・音の高さで伝える。

-- >>>DATA (gen_liminal.py が書く。手で触らない)
CONNS = {
  {
    id=1.0,
    focus={-0.52,1.7,6.3},
    lock=1.6,
    warn=12.0,
    center={0.0,1.2,14.42},
    note="door",
    shards={
      {
        k=1.0,
        ents={
          {
            n="C1_R_jamb",
            p={0.65,1.25,14.39},
            s={0.2,2.3,0.22}
          },
          {
            n="C1_R_head",
            p={0.325,2.3,14.39},
            s={0.65,0.2,0.22}
          },
          {
            n="C1_R_sill",
            p={0.325,0.05,14.39},
            s={0.65,0.1,0.22}
          },
          {
            n="C1_R_g1",
            p={0.565,1.15,14.512},
            s={0.03,2.1,0.03}
          },
          {
            n="C1_R_g2",
            p={0.275,2.185,14.512},
            s={0.55,0.03,0.03}
          },
          {
            n="C1_R_g3",
            p={0.275,0.115,14.512},
            s={0.55,0.03,0.03}
          }
        },
        pts={
          {0.75,2.4,14.527},
          {0.0,2.4,14.527},
          {0.75,0.0,14.527},
          {0.0,0.0,14.527},
          {0.75,2.4,14.28},
          {0.0,2.4,14.28},
          {0.75,0.0,14.28},
          {0.0,0.0,14.28}
        }
      },
      {
        k=0.42,
        ents={
          {
            n="C1_L_jamb",
            p={-0.65,1.25,14.39},
            s={0.2,2.3,0.22}
          },
          {
            n="C1_L_head",
            p={-0.325,2.3,14.39},
            s={0.65,0.2,0.22}
          },
          {
            n="C1_L_sill",
            p={-0.325,0.05,14.39},
            s={0.65,0.1,0.22}
          },
          {
            n="C1_L_g1",
            p={-0.565,1.15,14.512},
            s={0.03,2.1,0.03}
          },
          {
            n="C1_L_g2",
            p={-0.275,2.185,14.512},
            s={0.55,0.03,0.03}
          },
          {
            n="C1_L_g3",
            p={-0.275,0.115,14.512},
            s={0.55,0.03,0.03}
          }
        },
        pts={
          {0.0,2.4,14.527},
          {-0.75,2.4,14.527},
          {0.0,0.0,14.527},
          {-0.75,0.0,14.527},
          {0.0,2.4,14.28},
          {-0.75,2.4,14.28},
          {0.0,0.0,14.28},
          {-0.75,0.0,14.28}
        }
      }
    },
    glows={
      "C1_R_g1",
      "C1_R_g2",
      "C1_R_g3",
      "C1_L_g1",
      "C1_L_g2",
      "C1_L_g3"
    },
    solids={

    },
    movers={
      {
        n="C1_Panel",
        to={0.0,-1.25,14.65},
        dur=1.5,
        delay=0.55
      }
    },
    lights={

    },
    hinges={

    }
  },
  {
    id=2.0,
    focus={-6.3,1.7,18.3},
    lock=1.4,
    warn=11.0,
    center={0.15,0.0,28.75},
    note="bridge",
    shards={
      {
        k=1.0,
        ents={
          {
            n="C2_s0",
            p={-3.7125,-0.12,24.3625},
            s={1.7,0.24,3.877}
          },
          {
            n="C2_s0e0",
            p={-4.328,0.02,24.9043},
            s={0.055,0.04,3.837}
          },
          {
            n="C2_s0e2",
            p={-3.097,0.02,23.8207},
            s={0.055,0.04,3.837}
          }
        },
        pts={
          {-2.8625,0.04,26.8228},
          {-4.5625,0.04,26.8228},
          {-2.8625,-0.24,26.8228},
          {-4.5625,-0.24,26.8228},
          {-2.8625,0.04,21.9022},
          {-4.5625,0.04,21.9022},
          {-2.8625,-0.24,21.9022},
          {-4.5625,-0.24,21.9022}
        }
      },
      {
        k=0.72,
        ents={
          {
            n="C2_s1",
            p={-1.1375,-0.12,27.2875},
            s={1.7,0.24,3.877}
          },
          {
            n="C2_s1e0",
            p={-1.753,0.02,27.8293},
            s={0.055,0.04,3.837}
          },
          {
            n="C2_s1e2",
            p={-0.522,0.02,26.7457},
            s={0.055,0.04,3.837}
          }
        },
        pts={
          {-0.2875,0.04,29.7478},
          {-1.9875,0.04,29.7478},
          {-0.2875,-0.24,29.7478},
          {-1.9875,-0.24,29.7478},
          {-0.2875,0.04,24.8272},
          {-1.9875,0.04,24.8272},
          {-0.2875,-0.24,24.8272},
          {-1.9875,-0.24,24.8272}
        }
      },
      {
        k=0.53,
        ents={
          {
            n="C2_s2",
            p={1.4375,-0.12,30.2125},
            s={1.7,0.24,3.877}
          },
          {
            n="C2_s2e0",
            p={0.822,0.02,30.7543},
            s={0.055,0.04,3.837}
          },
          {
            n="C2_s2e2",
            p={2.053,0.02,29.6707},
            s={0.055,0.04,3.837}
          }
        },
        pts={
          {2.2875,0.04,32.6728},
          {0.5875,0.04,32.6728},
          {2.2875,-0.24,32.6728},
          {0.5875,-0.24,32.6728},
          {2.2875,0.04,27.7522},
          {0.5875,0.04,27.7522},
          {2.2875,-0.24,27.7522},
          {0.5875,-0.24,27.7522}
        }
      },
      {
        k=0.4,
        ents={
          {
            n="C2_s3",
            p={4.0125,-0.12,33.1375},
            s={1.7,0.24,3.877}
          },
          {
            n="C2_s3e0",
            p={3.397,0.02,33.6793},
            s={0.055,0.04,3.837}
          },
          {
            n="C2_s3e2",
            p={4.628,0.02,32.5957},
            s={0.055,0.04,3.837}
          }
        },
        pts={
          {4.8625,0.04,35.5978},
          {3.1625,0.04,35.5978},
          {4.8625,-0.24,35.5978},
          {3.1625,-0.24,35.5978},
          {4.8625,0.04,30.6772},
          {3.1625,0.04,30.6772},
          {4.8625,-0.24,30.6772},
          {3.1625,-0.24,30.6772}
        }
      }
    },
    glows={
      "C2_s0e0",
      "C2_s0e2",
      "C2_s1e0",
      "C2_s1e2",
      "C2_s2e0",
      "C2_s2e2",
      "C2_s3e0",
      "C2_s3e2"
    },
    solids={
      {
        n="C2_h1",
        p={-1.1375,-0.12,27.2875}
      },
      {
        n="C2_h2",
        p={1.4375,-0.12,30.2125}
      },
      {
        n="C2_h3",
        p={4.0125,-0.12,33.1375}
      }
    },
    movers={

    },
    lights={

    },
    hinges={

    }
  },
  {
    id=3.0,
    focus={-5.4,1.7,53.6},
    lock=2.2,
    warn=13.0,
    center={6.1,1.8,55.0},
    note="stair",
    shards={
      {
        k=1.0,
        ents={
          {
            n="C3_s0",
            p={6.1,0.1733,50.4},
            s={1.7,0.22,0.8}
          },
          {
            n="C3_r0",
            p={6.1,-0.0233,50.02},
            s={1.7,0.2833,0.04}
          },
          {
            n="C3_e0",
            p={5.28,0.2883,50.4},
            s={0.055,0.04,0.76}
          },
          {
            n="C3_s1",
            p={6.1,0.4567,51.2},
            s={1.7,0.22,0.8}
          },
          {
            n="C3_r1",
            p={6.1,0.26,50.82},
            s={1.7,0.2833,0.04}
          },
          {
            n="C3_e1",
            p={5.28,0.5717,51.2},
            s={0.055,0.04,0.76}
          },
          {
            n="C3_s2",
            p={6.1,0.74,52.0},
            s={1.7,0.22,0.8}
          },
          {
            n="C3_r2",
            p={6.1,0.5433,51.62},
            s={1.7,0.2833,0.04}
          },
          {
            n="C3_e2",
            p={5.28,0.855,52.0},
            s={0.055,0.04,0.76}
          }
        },
        pts={
          {6.95,0.875,52.4},
          {5.25,0.875,52.4},
          {6.95,-0.1649,52.4},
          {5.25,-0.1649,52.4},
          {6.95,0.875,50.0},
          {5.25,0.875,50.0},
          {6.95,-0.1649,50.0},
          {5.25,-0.1649,50.0}
        }
      },
      {
        k=0.62,
        ents={
          {
            n="C3_s3",
            p={6.1,1.0233,52.8},
            s={1.7,0.22,0.8}
          },
          {
            n="C3_r3",
            p={6.1,0.8267,52.42},
            s={1.7,0.2833,0.04}
          },
          {
            n="C3_e3",
            p={5.28,1.1383,52.8},
            s={0.055,0.04,0.76}
          },
          {
            n="C3_s4",
            p={6.1,1.3067,53.6},
            s={1.7,0.22,0.8}
          },
          {
            n="C3_r4",
            p={6.1,1.11,53.22},
            s={1.7,0.2833,0.04}
          },
          {
            n="C3_e4",
            p={5.28,1.4217,53.6},
            s={0.055,0.04,0.76}
          },
          {
            n="C3_s5",
            p={6.1,1.59,54.4},
            s={1.7,0.22,0.8}
          },
          {
            n="C3_r5",
            p={6.1,1.3933,54.02},
            s={1.7,0.2833,0.04}
          },
          {
            n="C3_e5",
            p={5.28,1.705,54.4},
            s={0.055,0.04,0.76}
          },
          {
            n="C3_s6",
            p={6.1,1.8733,55.2},
            s={1.7,0.22,0.8}
          },
          {
            n="C3_r6",
            p={6.1,1.6766,54.82},
            s={1.7,0.2833,0.04}
          },
          {
            n="C3_e6",
            p={5.28,1.9883,55.2},
            s={0.055,0.04,0.76}
          }
        },
        pts={
          {6.95,2.0083,55.6},
          {5.25,2.0083,55.6},
          {6.95,0.685,55.6},
          {5.25,0.685,55.6},
          {6.95,2.0083,52.4},
          {5.25,2.0083,52.4},
          {6.95,0.685,52.4},
          {5.25,0.685,52.4}
        }
      },
      {
        k=0.46,
        ents={
          {
            n="C3_s7",
            p={6.1,2.1566,56.0},
            s={1.7,0.22,0.8}
          },
          {
            n="C3_r7",
            p={6.1,1.96,55.62},
            s={1.7,0.2833,0.04}
          },
          {
            n="C3_e7",
            p={5.28,2.2716,56.0},
            s={0.055,0.04,0.76}
          },
          {
            n="C3_s8",
            p={6.1,2.44,56.8},
            s={1.7,0.22,0.8}
          },
          {
            n="C3_r8",
            p={6.1,2.2433,56.42},
            s={1.7,0.2833,0.04}
          },
          {
            n="C3_e8",
            p={5.28,2.555,56.8},
            s={0.055,0.04,0.76}
          },
          {
            n="C3_s9",
            p={6.1,2.7233,57.6},
            s={1.7,0.22,0.8}
          },
          {
            n="C3_r9",
            p={6.1,2.5266,57.22},
            s={1.7,0.2833,0.04}
          },
          {
            n="C3_e9",
            p={5.28,2.8383,57.6},
            s={0.055,0.04,0.76}
          }
        },
        pts={
          {6.95,2.8583,58.0},
          {5.25,2.8583,58.0},
          {6.95,1.8183,58.0},
          {5.25,1.8183,58.0},
          {6.95,2.8583,55.6},
          {5.25,2.8583,55.6},
          {6.95,1.8183,55.6},
          {5.25,1.8183,55.6}
        }
      },
      {
        k=0.355,
        ents={
          {
            n="C3_s10",
            p={6.1,3.0066,58.4},
            s={1.7,0.22,0.8}
          },
          {
            n="C3_r10",
            p={6.1,2.81,58.02},
            s={1.7,0.2833,0.04}
          },
          {
            n="C3_e10",
            p={5.28,3.1216,58.4},
            s={0.055,0.04,0.76}
          },
          {
            n="C3_s11",
            p={6.1,3.29,59.2},
            s={1.7,0.22,0.8}
          },
          {
            n="C3_r11",
            p={6.1,3.0933,58.82},
            s={1.7,0.2833,0.04}
          },
          {
            n="C3_e11",
            p={5.28,3.405,59.2},
            s={0.055,0.04,0.76}
          }
        },
        pts={
          {6.95,3.425,59.6},
          {5.25,3.425,59.6},
          {6.95,2.6684,59.6},
          {5.25,2.6684,59.6},
          {6.95,3.425,58.0},
          {5.25,3.425,58.0},
          {6.95,2.6684,58.0},
          {5.25,2.6684,58.0}
        }
      }
    },
    glows={
      "C3_e0",
      "C3_e1",
      "C3_e2",
      "C3_e3",
      "C3_e4",
      "C3_e5",
      "C3_e6",
      "C3_e7",
      "C3_e8",
      "C3_e9",
      "C3_e10",
      "C3_e11"
    },
    solids={
      {
        n="C3_h3",
        p={6.1,1.0233,52.8}
      },
      {
        n="C3_h4",
        p={6.1,1.3067,53.6}
      },
      {
        n="C3_h5",
        p={6.1,1.59,54.4}
      },
      {
        n="C3_h6",
        p={6.1,1.8733,55.2}
      },
      {
        n="C3_h7",
        p={6.1,2.1566,56.0}
      },
      {
        n="C3_h8",
        p={6.1,2.44,56.8}
      },
      {
        n="C3_h9",
        p={6.1,2.7233,57.6}
      },
      {
        n="C3_h10",
        p={6.1,3.0066,58.4}
      },
      {
        n="C3_h11",
        p={6.1,3.29,59.2}
      }
    },
    movers={

    },
    lights={

    },
    hinges={

    }
  },
  {
    id=4.0,
    focus={5.55,5.1,69.2},
    lock=2.0,
    warn=13.0,
    center={6.1,4.6,79.9},
    note="exit",
    shards={
      {
        k=1.0,
        ents={
          {
            n="C4_signb",
            p={6.1,5.96,79.9},
            s={0.68,0.32,0.06}
          },
          {
            n="C4_sign",
            p={6.1,5.96,79.855},
            s={0.62,0.26,0.03}
          }
        },
        pts={
          {6.44,6.12,79.93},
          {5.76,6.12,79.93},
          {6.44,5.8,79.93},
          {5.76,5.8,79.93},
          {6.44,6.12,79.84},
          {5.76,6.12,79.84},
          {6.44,5.8,79.84},
          {5.76,5.8,79.84}
        }
      },
      {
        k=0.55,
        ents={
          {
            n="C4_L_jamb",
            p={5.45,4.65,79.92},
            s={0.2,2.3,0.22}
          },
          {
            n="C4_L_head",
            p={5.775,5.7,79.92},
            s={0.65,0.2,0.22}
          },
          {
            n="C4_L_sill",
            p={5.775,3.45,79.92},
            s={0.65,0.1,0.22}
          },
          {
            n="C4_L_g1",
            p={5.535,4.55,80.042},
            s={0.03,2.1,0.03}
          },
          {
            n="C4_L_g2",
            p={5.825,5.585,80.042},
            s={0.55,0.03,0.03}
          },
          {
            n="C4_L_g3",
            p={5.825,3.515,80.042},
            s={0.55,0.03,0.03}
          }
        },
        pts={
          {6.1,5.8,80.057},
          {5.35,5.8,80.057},
          {6.1,3.4,80.057},
          {5.35,3.4,80.057},
          {6.1,5.8,79.81},
          {5.35,5.8,79.81},
          {6.1,3.4,79.81},
          {5.35,3.4,79.81}
        }
      },
      {
        k=0.35,
        ents={
          {
            n="C4_R_jamb",
            p={6.75,4.65,79.92},
            s={0.2,2.3,0.22}
          },
          {
            n="C4_R_head",
            p={6.425,5.7,79.92},
            s={0.65,0.2,0.22}
          },
          {
            n="C4_R_sill",
            p={6.425,3.45,79.92},
            s={0.65,0.1,0.22}
          },
          {
            n="C4_R_g1",
            p={6.665,4.55,80.042},
            s={0.03,2.1,0.03}
          },
          {
            n="C4_R_g2",
            p={6.375,5.585,80.042},
            s={0.55,0.03,0.03}
          },
          {
            n="C4_R_g3",
            p={6.375,3.515,80.042},
            s={0.55,0.03,0.03}
          }
        },
        pts={
          {6.85,5.8,80.057},
          {6.1,5.8,80.057},
          {6.85,3.4,80.057},
          {6.1,3.4,80.057},
          {6.85,5.8,79.81},
          {6.1,5.8,79.81},
          {6.85,3.4,79.81},
          {6.1,3.4,79.81}
        }
      },
      {
        k=0.72,
        ents={
          {
            n="C4_Leaf",
            p={6.1,4.5,79.8},
            s={1.06,2.16,0.06}
          },
          {
            n="C4_Knob",
            p={6.49,4.42,79.73},
            s={0.07,0.07,0.07}
          },
          {
            n="C4_Lfink",
            p={6.1,3.43,79.8},
            s={1.04,0.03,0.03}
          }
        },
        pts={
          {6.63,5.58,79.83},
          {5.57,5.58,79.83},
          {6.63,3.415,79.83},
          {5.57,3.415,79.83},
          {6.63,5.58,79.695},
          {5.57,5.58,79.695},
          {6.63,3.415,79.695},
          {5.57,3.415,79.695}
        }
      }
    },
    glows={
      "C4_L_g1",
      "C4_L_g2",
      "C4_L_g3",
      "C4_R_g1",
      "C4_R_g2",
      "C4_R_g3",
      "C4_Lfink"
    },
    solids={

    },
    movers={
      {
        n="C4_Panel",
        to={6.1,2.05,80.15},
        dur=1.6,
        delay=0.5
      }
    },
    lights={
      {
        n="C4_sign",
        to=1.0,
        dur=0.6,
        delay=0.35
      }
    },
    hinges={
      {
        n="C4_Leaf",
        p={5.946,4.668,76.832},
        piv={5.55,4.5,79.8},
        deg=-82.0,
        dur=1.5,
        delay=0.9
      },
      {
        n="C4_Knob",
        p={6.2268,4.6104,76.7816},
        piv={5.55,4.5,79.8},
        deg=-82.0,
        dur=1.5,
        delay=0.9
      },
      {
        n="C4_Lfink",
        p={5.946,3.8976,76.832},
        piv={5.55,4.5,79.8},
        deg=-82.0,
        dur=1.5,
        delay=0.9
      }
    }
  }
}
-- <<<DATA

local EYE_OFF = 0.80          -- 体の中心から目まで
local SPEED   = 3.05
local ACCEL   = 13.0
local SENS    = 0.082
local CONE    = 26.0          -- 「見ている」と認める視野角(度)
local DWELL   = 0.28          -- 合った状態を保つ時間

-- 到達点(落ちた時の戻り先)。z を越えると進む
local CHECKS = {
    {x =  0.00, y = 0.90, z = -6.0, at = -1e9},
    {x =  0.00, y = 0.90, z = 16.6, at = 15.6},
    {x = -4.60, y = 0.90, z = 17.0, at = 17.6},   -- ★F2 の上に置かない(戻った瞬間に解ける)
    {x =  5.30, y = 0.90, z = 36.4, at = 35.6},
    {x =  5.50, y = 0.90, z = 47.6, at = 46.6},
    {x =  6.10, y = 4.30, z = 63.6, at = 62.6},
}

local function V(x, y, z) return Vec3.new(x, y, z) end
local function find(n)
    local e = scene:findEntity(n)
    if not (e and e:isValid()) then logWarn("Liminal: missing " .. n) return nil end
    return e
end
local function clamp(v, a, b) if v < a then return a elseif v > b then return b end return v end
local function smooth(t) t = clamp(t, 0, 1) return t * t * (3 - 2 * t) end

-- 対応点への視線の角度差(度)の最大値。atan2 版で 0 付近も安定して出る
-- ★Lua 5.4 は math.atan2 が消えて math.atan(y,x) になった。両方で動くようにする
local atan2 = math.atan2 or math.atan
local function alignError(ex, ey, ez, F, k, pts)
    local worst = 0.0
    for i = 1, #pts do
        local p = pts[i]
        local ax, ay, az = p[1] - ex, p[2] - ey, p[3] - ez
        local bx = F[1] + k * (p[1] - F[1]) - ex
        local by = F[2] + k * (p[2] - F[2]) - ey
        local bz = F[3] + k * (p[3] - F[3]) - ez
        local cx = ay * bz - az * by
        local cy = az * bx - ax * bz
        local cz = ax * by - ay * bx
        local cross = math.sqrt(cx * cx + cy * cy + cz * cz)
        local dot = ax * bx + ay * by + az * bz
        local d = math.deg(atan2(cross, dot))
        if d > worst then worst = d end
    end
    return worst
end

local function applyShard(sh, kk)
    local F = sh.F
    for i = 1, #sh.ents do
        local r = sh.ents[i]
        if r.e then
            r.e.transform.position = V(F[1] + kk * (r.p[1] - F[1]),
                                       F[2] + kk * (r.p[2] - F[2]),
                                       F[3] + kk * (r.p[3] - F[3]))
            r.e.transform.scale = V(r.s[1] * kk, r.s[2] * kk, r.s[3] * kk)
        end
    end
end

local function setGlow(c, power)
    for i = 1, #c.glowE do
        scene:setMeshParams(c.glowE[i], 1.0, 0.84, 0.52, power)
    end
end

function OnStart(self)
    self.body = find("LM_Player")
    self.cam  = find("LM_Camera")
    self.ring = find("LM_Ring")
    self.dot  = find("LM_Dot")
    self.hint = find("LM_Hint")
    self.endt = find("LM_End")

    self.yaw, self.pitch = 0.0, 0.0
    self.vx, self.vz = 0.0, 0.0
    self.t, self.cp, self.stepT = 0.0, 1, 0.0
    self.done, self.doneT = false, 0.0
    self.tweens = {}
    self.swings = {}
    self.ringA, self.ringF = 0.0, 0.0

    -- 継ぎ目のテーブルを実体化(entity をここで 1 回だけ引く)
    self.conns = {}
    for i = 1, #CONNS do
        local d = CONNS[i]
        local c = { id = d.id, F = d.focus, lock = d.lock, warn = d.warn, center = d.center,
                    note = d.note, shards = {}, glowE = {}, solids = d.solids, movers = d.movers,
                    lights = d.lights, hinges = d.hinges or {}, locked = false, anim = -1,
                    a = 0.0, err = 999.0, hold = 0.0, tick = 0 }
        for s = 1, #d.shards do
            local sd = d.shards[s]
            local sh = { k = sd.k, pts = sd.pts, F = d.focus, ents = {} }
            for j = 1, #sd.ents do
                local r = sd.ents[j]
                local e = find(r.n)
                sh.ents[#sh.ents + 1] = { e = e, p = r.p, s = r.s }
            end
            applyShard(sh, sd.k)
            c.shards[#c.shards + 1] = sh
        end
        for g = 1, #d.glows do
            local e = find(d.glows[g])
            if e then c.glowE[#c.glowE + 1] = e end
        end
        setGlow(c, 1.25)
        self.conns[#self.conns + 1] = c
    end

    -- 音: 部屋の唸りと、合い具合のドローン(音量 0 から始める)
    self.drone = audio:playSFXId("audio/lm/drone.wav", true, 0.0)
    self.hum = {}
    for _, p in ipairs({ { 0, 2.4, 1 }, { 0, 2.4, 13 }, { -4.5, 3.0, 20.6 }, { 0, 3.0, 28.8 },
                         { 4.9, 5.6, 55.5 }, { 6.1, 6.0, 68.5 } }) do
        self.hum[#self.hum + 1] = audio:playSpatialId("audio/lm/buzz.wav", p[1], p[2], p[3],
                                                      2.0, 13.0, 0.30, true)
    end

    -- ★蛍光灯の明滅。1 部屋に 1 本だけ。全部やると「演出」になって嘘くさくなる
    for _, n in ipairs({ "A_tr+09_l", "B_tr9_29_l", "C_tr14_56_l" }) do
        local e = scene:findEntity(n)
        if e and e:isValid() then
            local l = e:light()
            if l then Flicker(l, "fluorescent") end
        end
    end

    -- ★MCP 検証用フックは Play のたびに必ず落とす(前回の値が残ると
    --   人が遊んだときに勝手に歩き出す)
    saveNum("lm_auto", 0); saveNum("lm_test", 0); saveNum("lm_warp", 0); saveNum("lm_tp", 0)
    for i = 1, 4 do saveNum(string.format("lm_c%d", i), 0) end
    saveNum("lm_clear", 0)

    scene:setUiColor(self.ring, 1.0, 0.86, 0.55, 0.0)
    scene:setUiFill(self.ring, 0.0)
    scene:setUiText(self.endt, "")
    scene:setUiColor(self.endt, 0.94, 0.93, 0.86, 0.0)
    input:setMouseCapture(true)
    saveNum("lm_locked", 0)
    log("LIMINAL: " .. #self.conns .. " joints. look, and it becomes.")
end

local function tweenTo(self, e, to, dur, delay)
    self.tweens[#self.tweens + 1] = { e = e, from = nil, to = to, dur = dur, t = -(delay or 0) }
end

-- 丁番まわりの回転。★エンジンの yaw は行ベクトル系なので
--   (x,z) -> (x cos + z sin, -x sin + z cos)。符号を間違えると扉が壁側へ開く
local function runSwings(self, dt)
    local i = 1
    while i <= #self.swings do
        local w = self.swings[i]
        w.t = w.t + dt
        if w.t >= 0 then
            local u = smooth(w.t / w.dur)
            local th = math.rad(w.deg * u)
            local dx, dz = w.p[1] - w.piv[1], w.p[3] - w.piv[3]
            local c_, s_ = math.cos(th), math.sin(th)
            w.e.transform.position = V(w.piv[1] + dx * c_ + dz * s_, w.p[2],
                                       w.piv[3] - dx * s_ + dz * c_)
            w.e.transform.rotation = V(0, w.deg * u, 0)
        end
        if w.t >= w.dur then table.remove(self.swings, i) else i = i + 1 end
    end
end


local function runTweens(self, dt)
    local i = 1
    while i <= #self.tweens do
        local w = self.tweens[i]
        w.t = w.t + dt
        if w.t >= 0 then
            if not w.from then
                local p = w.e.transform.position
                w.from = { p.x, p.y, p.z }
            end
            local u = smooth(w.t / w.dur)
            w.e.transform.position = V(w.from[1] + (w.to[1] - w.from[1]) * u,
                                       w.from[2] + (w.to[2] - w.from[2]) * u,
                                       w.from[3] + (w.to[3] - w.from[3]) * u)
        end
        if w.t >= w.dur then
            table.remove(self.tweens, i)
        else
            i = i + 1
        end
    end
end

local function beginLock(self, c)
    c.anim = 0.0
    audio:playSFX("audio/lm/lock.wav")
    fx:burst{ x = c.center[1], y = c.center[2], z = c.center[3], kind = "glow", count = 26,
              size = 0.30, sizeEnd = 0.0, life = 0.9, speed = 1.6, spread = 1.0,
              r = 1.0, g = 0.86, b = 0.55, intensity = 2.0, drag = 1.4 }
    log("LIMINAL joint " .. c.id .. " (" .. c.note .. ") resolved")
end

local function finishLock(self, c)
    for i = 1, #c.solids do
        local e = find(c.solids[i].n)
        if e then
            physics:removeRigidBody(e)
            e.transform.position = V(c.solids[i].p[1], c.solids[i].p[2], c.solids[i].p[3])
            physics:addRigidBody(e, 0, 1)
        end
    end
    for i = 1, #c.movers do
        local m = c.movers[i]
        local e = find(m.n)
        if e then
            physics:removeRigidBody(e)
            tweenTo(self, e, m.to, m.dur, m.delay)
        end
    end
    for i = 1, #c.lights do
        local l = c.lights[i]
        local e = find(l.n)
        if e then scene:setColor(e, l.to, l.to, l.to) end
        local le = scene:findEntity(l.n .. "_l")
        if le and le:isValid() then
            local lt = le:light()
            if lt then lt.intensity = 0.35 end
        end
    end
    for i = 1, #c.hinges do
        local h = c.hinges[i]
        local e = find(h.n)
        if e then
            self.swings[#self.swings + 1] = { e = e, p = h.p, piv = h.piv, deg = h.deg,
                                              dur = h.dur, t = -(h.delay or 0) }
        end
    end
    if #c.movers > 0 then audio:playSFX("audio/lm/reveal.wav") end
    c.locked = true
    local n = 0
    for i = 1, #self.conns do if self.conns[i].locked then n = n + 1 end end
    saveNum("lm_locked", n)
    saveNum(string.format("lm_c%d", c.id), 1)
end

function OnUpdate(self, dt)
    dt = math.min(dt, 0.06)
    self.t = self.t + dt
    -- Play 直後はシーン復元が transform を書き戻すので体を押し込む
    if self.t < 0.55 then
        physics:setPosition(self.body, V(CHECKS[1].x, CHECKS[1].y, CHECKS[1].z))
    end

    if keyPressed("ESC") then input:setMouseCapture(not input:isMouseCaptured()) end

    -- ------------------------------------------------ 視点
    if not self.done then
        if loadNum("lm_test", 0) > 0.5 then
            self.yaw = loadNum("lm_yaw", self.yaw)
            self.pitch = loadNum("lm_pitch", self.pitch)
        elseif input:isMouseCaptured() then
            self.yaw = self.yaw + input:getMouseDeltaX() * SENS
            self.pitch = self.pitch - input:getMouseDeltaY() * SENS
        end
        if keyDown("LEFT") then self.yaw = self.yaw - 90 * dt end
        if keyDown("RIGHT") then self.yaw = self.yaw + 90 * dt end
        if keyDown("UP") then self.pitch = self.pitch + 70 * dt end
        if keyDown("DOWN") then self.pitch = self.pitch - 70 * dt end
    end
    self.yaw = self.yaw % 360
    self.pitch = clamp(self.pitch, -78, 78)

    -- ------------------------------------------------ 移動
    local yr = math.rad(self.yaw)
    local wx, wz = 0.0, 0.0
    if not self.done then
        if keyDown("W") then wx = wx + math.sin(yr); wz = wz + math.cos(yr) end
        if keyDown("S") then wx = wx - math.sin(yr); wz = wz - math.cos(yr) end
        if keyDown("D") then wx = wx + math.cos(yr); wz = wz - math.sin(yr) end
        if keyDown("A") then wx = wx - math.cos(yr); wz = wz + math.sin(yr) end
    end
    -- ★MCP からの自動テスト用: 目的地(lm_gx, lm_gz)へ歩く。
    --   キー入力より後に上書きするので、人が遊ぶ時は一切影響しない(lm_auto=0)。
    if loadNum("lm_auto", 0) > 0.5 and not self.done then
        local q = self.body.transform.position
        local gx, gz = loadNum("lm_gx", q.x), loadNum("lm_gz", q.z)
        local dx, dz = gx - q.x, gz - q.z
        local d = math.sqrt(dx * dx + dz * dz)
        if d > 0.16 then
            wx, wz = dx / d, dz / d
            if loadNum("lm_test", 0) < 0.5 then self.yaw = math.deg(atan2(dx, dz)) end
        else
            wx, wz = 0, 0
        end
        saveNum("lm_gd", d)
    end
    local len = math.sqrt(wx * wx + wz * wz)
    local tx, tz = 0.0, 0.0
    if len > 0 then tx, tz = wx / len * SPEED, wz / len * SPEED end
    local f = clamp(ACCEL * dt, 0, 1)
    self.vx = self.vx + (tx - self.vx) * f
    self.vz = self.vz + (tz - self.vz) * f
    physics:move(self.body, self.vx, self.vz)

    local p = self.body.transform.position
    local ex, ey, ez = p.x, p.y + EYE_OFF, p.z
    self.cam.transform.position = V(ex, ey, ez)
    self.cam.transform.rotation = V(-self.pitch, self.yaw, 0)
    audio:setListener(ex, ey, ez)

    -- 足音(絨毯とタイルで替える)
    local moving = (self.vx * self.vx + self.vz * self.vz) > 1.2
    if moving then
        self.stepT = self.stepT + dt
        if self.stepT > 0.47 then
            self.stepT = 0.0
            local tile = (p.z > 40.5 and p.z < 62.0 and p.y < 2.0)
            audio:playSFX(tile and "audio/lm/step_hard.wav" or "audio/lm/step_soft.wav")
        end
    else
        self.stepT = 0.32
    end

    -- 到達点の更新と落下復帰
    for i = self.cp + 1, #CHECKS do
        if p.z > CHECKS[i].at then self.cp = i end
    end
    if p.y < -3.2 and not self.done then
        local c = CHECKS[self.cp]
        physics:setPosition(self.body, V(c.x, c.y, c.z))
        self.vx, self.vz = 0, 0
    end
    -- デバッグ移動(MCP 検証用)
    local tp = loadNum("lm_tp", 0)
    if tp > 0.5 then
        local c = CHECKS[math.floor(tp)]
        if c then
            physics:setPosition(self.body, V(c.x, c.y, c.z))
            self.body.transform.position = V(c.x, c.y, c.z)
            self.cp = math.floor(tp)
        end
        saveNum("lm_tp", 0)
    end
    local warp = loadNum("lm_warp", 0)
    if warp > 0.5 then
        physics:setPosition(self.body, V(loadNum("lm_wx", p.x), loadNum("lm_wy", p.y), loadNum("lm_wz", p.z)))
        saveNum("lm_warp", 0)
    end

    -- ------------------------------------------------ 継ぎ目
    local fx_, fy_, fz_ = math.sin(yr) * math.cos(math.rad(self.pitch)),
                          math.sin(math.rad(self.pitch)),
                          math.cos(yr) * math.cos(math.rad(self.pitch))
    local best, bestC = 0.0, nil
    for i = 1, #self.conns do
        local c = self.conns[i]
        if c.anim >= 0 then
            -- 溶接中: k を 1 へ
            c.anim = c.anim + dt / 0.85
            local u = smooth(c.anim)
            for s = 1, #c.shards do
                local sh = c.shards[s]
                applyShard(sh, sh.k + (1.0 - sh.k) * u)
            end
            setGlow(c, 5.2 * (1.0 - u) + 0.85)
            if c.anim >= 1.0 then
                c.anim = -1
                for s = 1, #c.shards do applyShard(c.shards[s], 1.0) end
                finishLock(self, c)
            end
        elseif c.locked then
            setGlow(c, math.max(0.55, 0.85 - (self.t - (c.doneAt or self.t)) * 0.25))
        else
            local dx, dy, dz = c.center[1] - ex, c.center[2] - ey, c.center[3] - ez
            local dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            local err, n = 0.0, 0
            -- ★遠すぎる継ぎ目は評価しない。ここで err を 0 のままにすると
            --   「遠くから覗いただけで確定」になるので、必ず 999 を入れること
            if dist < 34.0 then
                for s = 1, #c.shards do
                    local sh = c.shards[s]
                    if sh.k < 0.999 then
                        local e2 = alignError(ex, ey, ez, sh.F, sh.k, sh.pts)
                        if e2 > err then err = e2 end
                        n = n + 1
                    end
                end
            end
            if n == 0 then err = 999.0 end
            c.err = err
            local a = clamp(1.0 - err / c.warn, 0, 1)
            -- 見ているか(視線と継ぎ目の中心の角度)
            local dl = math.max(dist, 0.001)
            local cosv = (dx * fx_ + dy * fy_ + dz * fz_) / dl
            local looking = cosv > math.cos(math.rad(CONE))
            c.a = a
            if a > best and looking then best = a; bestC = c end
            setGlow(c, 1.25 + 4.4 * a * a * a)
            if looking and err < c.lock then
                c.hold = c.hold + dt
                if c.hold >= DWELL then beginLock(self, c); c.doneAt = self.t end
            else
                c.hold = 0.0
            end
            -- 近づいた合図(段階が上がった時だけ)
            local step = (a > 0.92 and 3) or (a > 0.75 and 2) or (a > 0.5 and 1) or 0
            if looking and step > c.tick then audio:playSFX("audio/lm/tick.wav") end
            c.tick = step
            saveNum(string.format("lm_e%d", c.id), err)
            saveNum(string.format("lm_a%d", c.id), a)
        end
    end

    -- ------------------------------------------------ HUD(環ひとつ)
    local ta = best
    self.ringA = self.ringA + (ta - self.ringA) * clamp(9.0 * dt, 0, 1)
    self.ringF = self.ringF + (ta - self.ringF) * clamp(14.0 * dt, 0, 1)
    scene:setUiColor(self.ring, 1.0, 0.86, 0.55, 0.86 * self.ringA ^ 0.8)
    scene:setUiFill(self.ring, self.ringF)
    if self.drone then
        audio:setVoiceVolume(self.drone, 0.34 * self.ringA ^ 1.4)
        audio:setVoicePitch(self.drone, 0.70 + 0.68 * self.ringA)
    end
    -- 操作の案内は 9 秒で消える(以後、画面に文字は出ない)
    local ha = clamp((11.0 - self.t) / 2.0, 0, 1) * 0.55
    if ha <= 0.005 then
        scene:setUiVisible(self.hint, false)      -- ★alpha 0 でも縁取りは残る。要素ごと消す
    else
        scene:setUiColor(self.hint, 0.92, 0.91, 0.85, ha)
    end

    -- ------------------------------------------------ 終わり
    if not self.done and p.z > 81.4 and p.y > 2.5 then
        self.done = true
        self.doneT = 0.0
        input:setMouseCapture(false)
        audio:playSFX("audio/lm/clear.wav")
        scene:setUiText(self.endt, "つながった")
        saveNum("lm_clear", 1)
        log("LIMINAL: complete")
    end
    if self.done then
        self.doneT = self.doneT + dt
        -- ★白く飛ばしっぱなしにすると UI もポストを浴びて文字が消える。
        --   閃光 -> 落ち着く、の 2 段にして、文字は落ち着いてから出す。
        local flash = clamp(self.doneT / 0.7, 0, 1)
        local settle = clamp((self.doneT - 0.7) / 1.3, 0, 1)
        post.set("exposure", 1.06 + 0.70 * flash - 0.45 * settle)
        local ta = clamp((self.doneT - 1.1) / 1.0, 0, 1)
        scene:setUiColor(self.endt, 0.12, 0.12, 0.11, ta)
        scene:setUiColor(self.ring, 1, 1, 1, 0)
        scene:setUiVisible(self.hint, self.doneT > 2.4)
        if self.doneT > 2.4 then
            if not self.endHint then
                self.endHint = true
                scene:setUiText(self.hint, "Enter")   -- setUiText は毎フレーム呼ばない
            end
            scene:setUiColor(self.hint, 0.20, 0.20, 0.18, 0.5)
        end
        if self.doneT > 2.6 and keyPressed("ENTER") then loadScene("scenes/stagedemo3.json") end
    end

    runTweens(self, dt)
    runSwings(self, dt)
    saveNum("lm_px", p.x); saveNum("lm_py", p.y); saveNum("lm_pz", p.z)
    saveNum("lm_yawr", self.yaw)
end
