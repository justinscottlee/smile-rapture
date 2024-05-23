import cv2
import numpy as np

def __stitch_images(stitch_candidates):
    print("Stitching images: ", len(stitch_candidates))
    # Start with the first image
    base_img, base_kp, base_desc = stitch_candidates[0]
    base_img = cv2.cvtColor(base_img, cv2.COLOR_GRAY2BGRA)  # Ensure image has alpha channel

    for img, kp, desc in stitch_candidates[1:]:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)  # Ensure image has alpha channel
        # Find homography between base image and current image
        flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=50))
        matches = flann.match(base_desc.astype(np.float32), desc.astype(np.float32))
        matches = sorted(matches, key=lambda x: x.distance)

        # Extract location of good matches
        points1 = np.zeros((len(matches), 2), dtype=np.float32)
        points2 = np.zeros((len(matches), 2), dtype=np.float32)

        for i, match in enumerate(matches):
            points1[i, :] = base_kp[match.queryIdx].pt
            points2[i, :] = kp[match.trainIdx].pt

        # Compute homography matrix
        H, _ = cv2.findHomography(points2, points1, method=cv2.RANSAC)

        # Calculate the size of the new canvas
        h1, w1 = base_img.shape[:2]
        h2, w2 = img.shape[:2]
        corners1 = np.array([[0, 0], [0, h1], [w1, h1], [w1, 0]], dtype=np.float32).reshape(-1, 1, 2)
        corners2 = np.array([[0, 0], [0, h2], [w2, h2], [w2, 0]], dtype=np.float32).reshape(-1, 1, 2)
        transformed_corners2 = cv2.perspectiveTransform(corners2, H)
        all_corners = np.concatenate((corners1, transformed_corners2), axis=0)
        [x_min, y_min] = np.int32(all_corners.min(axis=0).ravel() - 0.5)
        [x_max, y_max] = np.int32(all_corners.max(axis=0).ravel() + 0.5)

        # Adjust translations on the homography
        translation = np.array([[1, 0, -x_min], [0, 1, -y_min], [0, 0, 1]], dtype=np.float32)

        # Use homography to warp images
        width = x_max - x_min
        height = y_max - y_min
        img_warped = cv2.warpPerspective(img, translation.dot(H), (width, height), borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))
        
        # Blend the images together
        canvas = cv2.warpPerspective(base_img, translation, (width, height), borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))
        canvas = cv2.max(canvas, img_warped)

        # Update base image
        base_img = canvas

    return cv2.cvtColor(base_img, cv2.COLOR_BGRA2GRAY)

def demosaic(images):
    """
    Inputs: A list of grayscale images (with an alpha channel) that may or may not all overlap.
    Outputs: The minimum set of PNG images that are overlapped together with non-overlapping regions filled with alpha=0.
    """
    flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=50))
    orb = cv2.ORB_create(nfeatures=1000000)
    done = False

    while not done:
        matched = False
        key_desc = []
        for img in images:
            key, desc = orb.detectAndCompute(img, None)
            key_desc.append((key, desc))
        for i in range(len(images)):
            image1 = images[i]
            key1 = key_desc[i][0]
            desc1 = key_desc[i][1]
            for j in range(i+1, len(images)):
                image2 = images[j]
                key2 = key_desc[j][0]
                desc2 = key_desc[j][1]
                if i != j:
                    # Match descriptors
                    matches_ij = flann.knnMatch(key_desc[i][1].astype(np.float32), key_desc[j][1].astype(np.float32), k=2)

                    good_matches = []

                    for (m, n) in matches_ij:
                        if m.distance < 0.7 * n.distance:
                            good_matches.append(m)

                    if len(matches_ij) >= 10:
                        src_pts = np.float32([key_desc[i][0][m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                        dst_pts = np.float32([key_desc[j][0][m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

                        print(f"Inliers {i}->{j}: ", np.sum(mask), end="")
                        if (mask is not None) and (np.sum(mask) < 20):
                            print(" -> Insufficient overlap")
                        else:
                            print(" -> Good Match")
                            newimage = __stitch_images([(image1, key1, desc1), (image2, key2, desc2)])
                            images.append(newimage)
                            del images[j]
                            del images[i]
                            matched = True
                            break
            if matched:
                break
        
        if not matched:
            done = True
