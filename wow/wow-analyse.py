

import numpy as np
import os
import matplotlib.colors
import matplotlib.pyplot as plt
import sys
import json

from pathlib import Path

from scipy.special.cython_special import cosdg
from tqdm import tqdm


matplotlib.use('TkAgg')
plt.ion()


FILE = Path('../DATA/AM_full_inc_spinup.wow')
JSON_FILE = FILE.with_suffix('.tbc.json')
FILE_DATA = np.fromfile(FILE, dtype=np.int32)





NTSC = False
# FIELD_WIDTH = 910
# FIELD_HEIGHT = 273
# FIELD_HEIGHT = 263
FRAME_HEIGHT = 625 # (fieldheight from json * 2 - 1) - the minus one to remove the 2 half lines that are included
FIELD_HEIGHT = FRAME_HEIGHT / 2

# can get the PAN/NTSC and field sizes from the JSON file
# with open(JSON_FILE) as f:
#     json_data = json.load(f)
#
#     FIELDS = []
#     for field in json_data['fields']:
#         is_first = field['isFirstField']
#         raw_wow = field['wow']
#
#         line_count = 312 if is_first else 313
#         line_offset = 3 if is_first else 4  # todo check & see comment about 0-based lines *before* downscaling
#         wow = raw_wow[line_offset:line_count + line_offset]
#         FIELDS.extend(wow)



min_radius =50  # maybe 55
max_radius = 150 # need to check disc size from the VBI and maybe 145
delta_radius = max_radius - min_radius
render_size = 250
graphic_square = np.zeros(((render_size * 2) + 1, (render_size * 2) + 1))


total_frames = FILE_DATA.shape[0] // FRAME_HEIGHT
frame_metadata = np.empty((total_frames))


radius = None
angle_rads = None


# todo - populate with NULL




with open(FILE.with_suffix('.csv'), 'w') as f:
    # find the offset between each pair of frames
    frame = -1

    TEST_MIN = -int(FIELD_HEIGHT)
    TEST_CENTER = 0
    TEST_MAX = +int(FIELD_HEIGHT)

    lines_from_start_of_disc = 0
    total_revolutions = 0

    fit_line = []
    fit_start = 10  # window length

    bar = tqdm(total=total_frames)

    print(
        'frame',
        'best_i',
        'best_err',
        #'next_i',
        #'next_err',
        #'error',
        #'FRAME_HEIGHT',
        #'lines_from_start_of_disc',
        #'frame_ratio_of_revolution',
        'total_revolutions',
        'revolution_floor',
        #'remainder_revolution',
        'angle_rads',
        'radius',

        sep=',', file=f)

    while True: # frame < 10000:
        frame += 1
        bar.update(1)

        if frame > fit_start:
            last_avg = int(np.nanmean(fit_line[frame - fit_start:frame]))  # + TEST_MIN_START
            TEST_MIN = last_avg - 30
            TEST_CENTER = last_avg
            TEST_MAX = last_avg + 30

        # todo; calculate max offset given current TEST_MAX

        best_i = np.nan
        best_err = np.inf
        next_i = np.nan
        next_err = np.inf


        for offset in range(TEST_MIN, TEST_MAX + 1):
            ip = (frame + 0) * FRAME_HEIGHT
            iq = (frame + 1) * FRAME_HEIGHT + offset

            p = FILE_DATA[ip: ip + FRAME_HEIGHT]
            q = FILE_DATA[iq: iq + FRAME_HEIGHT]

            if p.shape != q.shape:
                break # todo could be continue

            diff = p - q
            error = np.mean(np.abs(diff))

            if error < best_err:
                next_err = best_err
                next_i = best_i
                best_err = error
                best_i = offset

        else:
            last_radius = radius
            last_angle_rads = angle_rads


            fit_line.append(best_i)
            error = abs(next_err - best_err) / best_err
            lines_per_revolution = FRAME_HEIGHT + best_i
            lines_from_start_of_disc += FRAME_HEIGHT
            frame_ratio_of_revolution = FRAME_HEIGHT / lines_per_revolution
            total_revolutions += frame_ratio_of_revolution
            revolution_floor = np.floor(total_revolutions)
            remainder_revolution = total_revolutions - revolution_floor
            angle_rads=remainder_revolution * (2 * np.pi)
            cos = np.cos(angle_rads)
            sin = np.sin(angle_rads)
            # 50mm internal radius (Maybe 55 - need to go and read spec for PAL+NTSC
            # 150m external radius
            # Need to wrk out what to do with >54000 revs may need to post process
            # 100mm of surface area and therefore 100 tracks per mm and a total of 54000 revolutions
            radius = min_radius + (total_revolutions / (54000 / delta_radius))

            x = render_size + (sin * radius * (render_size / max_radius))
            y = render_size + (cos * radius * (render_size / max_radius))
            # render_size
            graphic_square[int(x),int(y)] = FILE_DATA[(frame + 0) * FRAME_HEIGHT]

            frame_metadata[frame] = best_i

            print(
                frame,
                best_i,
                best_err,
                #next_i,
                #next_err,
                #error,
                # FRAME_HEIGHT,
                # lines_from_start_of_disc,
                # frame_ratio_of_revolution,
                total_revolutions,
                revolution_floor,
                #remainder_revolution,
                angle_rads,
                radius,

                sep=',', file=f)

            continue
        break  # break outer if inner broke

    bar.close()

chunk_size = 100

# when testing there was only an extra 14 video lines added for each 1000 frames.
# This is not worth rescaling for the match



with open(FILE.with_suffix('.coarse.csv'), 'w') as f:
    frame = 1 - chunk_size
    while True: # frame < 10000:
        frame += chunk_size
        comparison_frame = frame + chunk_size
        try:

            length_p = int(frame_metadata[frame])
            length_q = int(frame_metadata[comparison_frame])
            ip = (frame ) * FRAME_HEIGHT
            iq = (comparison_frame) * FRAME_HEIGHT

            p_length = p.shape[0]
            q_length = q.shape[0]
            compare_length = (2 * p_length) - q_length

            p = FILE_DATA[ip: ip + FRAME_HEIGHT + length_p]
            q = FILE_DATA[iq: iq + FRAME_HEIGHT + length_q]

            # print(frame, p.shape[0], q.shape[0], q.shape[0] - p.shape[0])

            if True:

                p2 = np.concatenate((p, p))

                # corr = np.correlate(p2, q)

                best_i = np.nan
                best_err = np.inf
                next_i = np.nan
                next_err = np.inf

                for offset in range(0, (2 * p_length) - q.shape[0]):


                    p_comp = p2[offset: offset + q.shape[0]]


                    if p_comp.shape != q.shape:
                        continue
                        break  # todo could be continue

                    diff = p_comp - q
                    error = np.mean(np.abs(diff))

                    if error < best_err:
                        next_err = best_err
                        next_i = best_i
                        best_err = error
                        best_i = offset
                else:
                    print(
                        frame,
                        q.shape[0] ,
                        p.shape[0],
                        q.shape[0] - p.shape[0],
                        offset,
                        q.shape[0] - offset,
                        offset / chunk_size
                    )






        except Exception as e:
            continue










breakpoint()

graphic_square = np.where(graphic_square == 0, np.nan, graphic_square)
plt.figure(figsize=(12, 6))
plt.imshow(graphic_square, cmap='rainbow', interpolation='none')  # , norm=PowerNorm(0.1))
plt.colorbar()

plt.show()
breakpoint()