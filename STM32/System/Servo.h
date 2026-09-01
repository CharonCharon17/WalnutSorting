#ifndef  __Servo_H__
#define  __Servo_H__

void Servo_Init(void);


void PWM_SetCompare1(uint16_t Compare);
void PWM_SetCompare2(uint16_t Compare);

void Servo_SetAngle_R(float Angle);
void Servo_SetAngle_L(float Angle);
#endif
