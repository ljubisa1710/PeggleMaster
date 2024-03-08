import cv2
import numpy as np
import pyautogui
import time
import pygetwindow as gw

def load_image(path):
    return cv2.imread(path)

def remove_centre_top_section(image, section_height, section_width):
    
    # Get image dimensions
    img_height, img_width = image.shape[:2]
    
    # Calculate the start and end points of the section
    start_x = img_width // 2 - section_width // 2
    end_x = start_x + section_width
    start_y = 0  # Start from the top
    end_y = start_y + section_height
    
    # Set the section to black (or any color you choose)
    image[start_y:end_y, start_x:end_x] = 0  # Using 0 for black
    
    # Save or display the modified image
    cv2.imwrite('modified_image.png', image)

def crop_image(name, image, top_pct, bottom_pct, left_pct, right_pct):
    top_boundary = int(image.shape[0] * top_pct)
    bottom_boundary = int(image.shape[0] * bottom_pct)
    left_boundary = int(image.shape[1] * left_pct)
    right_boundary = int(image.shape[1] * right_pct)
    cropped = image[top_boundary:bottom_boundary, left_boundary:right_boundary]
    cv2.imwrite('cropped_{}.png'.format(name), cropped)
    return cropped, top_boundary, left_boundary

def convert_to_hsv(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

def find_deep_orange_objects(hsv_image):
    orange_min = np.array([10, 150, 100], np.uint8)
    orange_max = np.array([20, 255, 255], np.uint8)
    mask = cv2.inRange(hsv_image, orange_min, orange_max)
    contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours

def draw_contours_and_centroids(cropped_image, contours, adjust_x, adjust_y, original_image):
    coordinates = []
    image_with_contours = cropped_image.copy()  # Use a copy for drawing contours
    for contour in contours:
        M = cv2.moments(contour)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            full_image_cX = cX + adjust_x
            full_image_cY = cY + adjust_y
            coordinates.append((full_image_cX, full_image_cY))
            cv2.drawContours(image_with_contours, [contour], -1, (0, 255, 0), 2)
            cv2.circle(original_image, (full_image_cX, full_image_cY), 5, (255, 0, 0), -1)
    cv2.imwrite('image_with_contours.png', image_with_contours)
    cv2.imwrite('image_with_peg_locations.png', original_image)
    return coordinates

def template_matching(source_image, template_image):
    source_gray = cv2.cvtColor(source_image, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(source_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    return result

def draw_template_match(image, result, template_image, found):
    if found:
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        top_left = max_loc
        w, h = template_image.shape[:-1]
        end_point = (top_left[0] + w, top_left[1] + h)
        cv2.rectangle(image, top_left, end_point, color=(0, 0, 255), thickness=2)
        print("Template found in the image: True")
    else:
        print("Template found in the image: False")
    cv2.imwrite('result_with_template_match.png', image)

def scale_coordinates(coordinates, window_position, window_size, image_width, image_height):
    window_x, window_y = window_position
    window_width, window_height = window_size
    scale_x = window_width / image_width
    scale_y = window_height / image_height
    scaled_and_adjusted_coordinates = [
        (int(x * scale_x) + window_x, int(y * scale_y) + window_y) for x, y in coordinates
    ]
    return scaled_and_adjusted_coordinates

def check_for_ball(image, shooting_ball_image):
    upper_threshold = 0.8
    lower_threshold = 0.7
    while upper_threshold >= lower_threshold:
        result = template_matching(image, shooting_ball_image)
        found = np.any(result >= upper_threshold)
        if found:
            return result, True
        upper_threshold -= 0.01
    return result, False

def screen_grab():
    title = "Peggle Deluxe" 
    window_info = None
    try:
        win = gw.getWindowsWithTitle(title)[0]  
        if win:
            win.activate()
            pyautogui.sleep(1)
            screenshot = pyautogui.screenshot(region=(win.left, win.top, win.width, win.height))
            screenshot.save(f'{title}_screenshot.png')
            window_info = (win.left, win.top), (win.width, win.height)
            print(f"Screenshot of '{title}' saved. Window info: {window_info}")
    except IndexError:
        print(f"No window with title '{title}' found.")
    return window_info

def main():
    time.sleep(5)
    window_info = screen_grab()
    if window_info is None:
        return
    window_position, window_size = window_info
    
    image_path = 'Peggle Deluxe_screenshot.png'
    shooting_ball_image_path = 'shooting_ball.png'
    shooting_ball_image = load_image(shooting_ball_image_path)
    image = load_image(image_path)
    
    cropped_image, top_boundary, left_boundary = crop_image('pegs', image, 0.20, 0.92, 0.11, 0.89)
    ball_location, _, _ = crop_image('ball', image, 0.1, 0.35, 0.35, 0.65)
    remove_centre_top_section(cropped_image, 80, 200)
    hsv = convert_to_hsv(cropped_image)
    contours = find_deep_orange_objects(hsv)
    coordinates = draw_contours_and_centroids(cropped_image, contours, left_boundary, top_boundary, image)
    coordinates = reversed(coordinates)
    
    result, found = check_for_ball(ball_location, shooting_ball_image)
    draw_template_match(image, result, shooting_ball_image, found)
    
    image_width, image_height = image.shape[1], image.shape[0]
    scaled_coordinates = scale_coordinates(coordinates, window_position, window_size, image_width, image_height)
    
    x, y = scaled_coordinates[0]
    _, found = check_for_ball(ball_location, shooting_ball_image)
    time.sleep(0.5)

    if (found):
        pyautogui.moveTo(x, y, duration=0.25)
        pyautogui.click()
        time.sleep(1)

if __name__ == "__main__":
    while(True):
        main()
