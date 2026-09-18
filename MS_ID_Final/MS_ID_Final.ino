#include <Wire.h>
#include <SimpleFOC.h>
#include <math.h>

// ---------------- BUZZER ----------------
#define BUZZER_PIN 15

const float linearLimitBufferRad = 0.25f;   // buzzer starts 0.25 rad before linear return
const int buzzerFreqHz = 2500;
const unsigned long buzzerPeriodMs = 500;   // total chirp cycle
const unsigned long buzzerOnMs = 60;        // chirp length

bool buzzerWasOff = true;

struct PositionPIDState {
  float Kp;
  float Ki;
  float Kd;

  float integral;
  float previousError;
  bool initialized;

  float outputLimit;    // |output| <= outputLimit
  float integralLimit;  // |integral| <= integralLimit

  unsigned long lastMicros;  // for dt
};

float rotAngle = 0.0;

//25,26 --> rotational unit

float startingAngle = 0.0f;
bool startCaptured = false;
bool recoveryMode = false;

float startingRotAngle = 0.0f;

float distanceOffset = 0.0f;
float heldDistanceValue = 0.0f;
bool recoveryJustStarted = false;

const float LINEAR_MM_PER_RAD = 8.98f;

bool waitingForStillness = false;
const float stillVelocityThreshold = 0.20f;  // rad/s, adjust as needed

const float bound = 8.00f;
const float returnTolerance = 0.05f;

float frozenLinearAngle = 0.0f;
bool frozenAngleValid = false;

PositionPIDState positionPID;

float positionTarget = 6.1f;

HardwareSerial mySerial(1);

extern MagneticSensorI2CConfig_s MT6701_I2C;
// extern MagneticSensorI2CConfig_s RotSensor;

TwoWire I2C_1 = TwoWire(0);  // uses I2C controller 0
TwoWire I2C_2 = TwoWire(1);  // uses I2C controller 1

MagneticSensorI2C sensor1(MT6701_I2C);
MagneticSensorI2C sensor2(MT6701_I2C);

unsigned long lastSend = 0;

// 3, 11 --> 32, 33
// 9, 10 --> 4, 5
// 5, 6 --> 16, 17

BLDCMotor motor = BLDCMotor(4);
// BLDCDriver6PWM driver = BLDCDriver6PWM(33, 32, 5, 4, 17, 16, 19);
BLDCDriver6PWM driver = BLDCDriver6PWM(
  14, 13,
  0, 2,
  23, 18,
  27);

float target_velocity = 15.0f;
float targetAngle = 0;
float currentAngle = 0;
Commander command = Commander(Serial);

unsigned long lastPrintMillis = 0;
const unsigned long printInterval = 200;

float filteredVelocity = 0.0f;
unsigned long lastVelMicros = 0;

const float velTau = 0.15f;

float prevAngle = 0.0f;
unsigned long prevMicros = 0;
bool velInit = false;

// ---------------- ROTATIONAL SHIFTING WINDOW ----------------
const float rotBoundDeg = 180.0f;  // output always in [-8, 8]
float rotWindowOffsetDeg = 0.0f;
bool rotWindowInit = false;

const float rotShiftMarginDeg = 0.25f;   // must exceed bound by this much before shifting
const float rotDeadbandDeg = 0.05f;      // ignore tiny output jitter

// -----------------------------------------------------------

void i2cRecover(int sclPin, int sdaPin) {
  pinMode(sclPin, OUTPUT_OPEN_DRAIN);
  pinMode(sdaPin, OUTPUT_OPEN_DRAIN);
  digitalWrite(sdaPin, HIGH);
  digitalWrite(sclPin, HIGH);
  delay(1);

  for (int i = 0; i < 9; i++) {
    digitalWrite(sclPin, LOW);
    delayMicroseconds(5);
    digitalWrite(sclPin, HIGH);
    delayMicroseconds(5);
  }

  digitalWrite(sdaPin, LOW);
  delayMicroseconds(5);
  digitalWrite(sclPin, HIGH);
  delayMicroseconds(5);
  digitalWrite(sdaPin, HIGH);
  delayMicroseconds(5);

  Wire.begin(sdaPin, sclPin);  // SDA first, SCL second
  Wire.setClock(100000);
  Wire.setTimeOut(50);  // << was 2ms
}

float radToDeg(float rad) {
  return rad * 180.0f / PI;
}

// Keeps output inside [-8, 8], but shifts the reference window when exceeded
float getSlidingWindowAngleDeg(float relativeAngleDeg) {
  if (!rotWindowInit) {
    rotWindowInit = true;
    rotWindowOffsetDeg = 0.0f;
  }

  float outputDeg = relativeAngleDeg - rotWindowOffsetDeg;

  // only shift if you go clearly past the edge
  if (outputDeg > (rotBoundDeg + rotShiftMarginDeg)) {
    rotWindowOffsetDeg = relativeAngleDeg - rotBoundDeg;
    outputDeg = rotBoundDeg;
  } else if (outputDeg < -(rotBoundDeg + rotShiftMarginDeg)) {
    rotWindowOffsetDeg = relativeAngleDeg + rotBoundDeg;
    outputDeg = -rotBoundDeg;
  } else {
    // normal clamp inside hysteresis region
    if (outputDeg > rotBoundDeg) outputDeg = rotBoundDeg;
    if (outputDeg < -rotBoundDeg) outputDeg = -rotBoundDeg;
  }

  // remove tiny jitter around zero
  if (fabs(outputDeg) < rotDeadbandDeg) {
    outputDeg = 0.0f;
  }

  return outputDeg;
}

void resetRotWindow() {
  rotWindowOffsetDeg = 0.0f;
  rotWindowInit = true;
}

void updateBuzzerLinearLimit(float rawAngle) {
  if (!startCaptured) {
    noTone(BUZZER_PIN);
    buzzerWasOff = true;
    return;
  }

  float linearAngleFromStart = rawAngle - startingAngle;

  // Buzzer turns on shortly before the system enters recovery
  bool nearLinearLimit = fabs(linearAngleFromStart) >= (bound - linearLimitBufferRad);

  // Optional: keep buzzing during the actual waiting/recovery transition too
  if (waitingForStillness || recoveryMode) {
    nearLinearLimit = true;
  }

  if (!nearLinearLimit) {
    noTone(BUZZER_PIN);
    buzzerWasOff = true;
    return;
  }

  unsigned long now = millis();
  unsigned long phase = now % buzzerPeriodMs;

  // Non-blocking chirp: ON for buzzerOnMs, OFF for the rest of the cycle
  if (phase < buzzerOnMs) {
    tone(BUZZER_PIN, buzzerFreqHz);
    buzzerWasOff = false;
  } else {
    noTone(BUZZER_PIN);
    buzzerWasOff = true;
  }
}

void setup() {
  Serial.begin(115200);
  I2C_1.begin(21, 22);
  I2C_1.setClock(100000);
  I2C_1.setTimeOut(50);

  // Bus 2: SDA=25, SCL=26
  I2C_2.begin(25, 26);
  I2C_2.setClock(100000);
  I2C_2.setTimeOut(50);

  sensor1.init(&I2C_1);
  sensor2.init(&I2C_2);

  // sensor.init();
  motor.linkSensor(&sensor1);

  driver.voltage_power_supply = 8.0f;
  driver.pwm_frequency = 25000;
  driver.init();
  motor.linkDriver(&driver);

  motor.controller = MotionControlType::velocity_openloop;
  motor.voltage_limit = 6.0f;  // [V]
  motor.init();

  mySerial.begin(115200, SERIAL_8N1, 17, 16);

  pinMode(BUZZER_PIN, OUTPUT);
  noTone(BUZZER_PIN);

  Serial.println("Basic Variables initialized");

  delay(3000);

  //               Kp    Ki     Kd    outputLimit  integralLimit
  initPositionPID(4.0f, 1.0f, 0.0f, 15.0f, 0.0f);
  setPositionTarget(positionTarget);  // start by holding 0 rad

  Serial.println("Setup Complete");


}

void loop() {
  sensor1.update();
  sensor2.update();

  float rawAngle = readCurrentAngle();
  rotAngle = sensor2.getAngle();
  float velFilt = getFilteredVelocityFromAngle(rawAngle);

  

  // Capture starting angle once
  if (!startCaptured) {
    startingAngle = rawAngle;
    positionTarget = startingAngle;
    distanceOffset = 0.0f;
    heldDistanceValue = 0.0f;
    startingRotAngle = rotAngle;

    resetRotWindow();

    motor.disable();
    startCaptured = true;
  }

  updateBuzzerLinearLimit(rawAngle);

  // This is the value your output device should use
  float distanceValue = ((rawAngle - startingAngle) + distanceOffset) * LINEAR_MM_PER_RAD;

  // Rotational angle relative to start, in degrees
  float rotRelativeDeg = radToDeg(rotAngle - startingRotAngle);

  // Apply shifting window
  float rotOutputDeg = getSlidingWindowAngleDeg(rotRelativeDeg);

  // ---- IF OUT OF BOUNDS, WAIT FOR LOW VELOCITY BEFORE RECOVERY ----
  if (!recoveryMode && !waitingForStillness && fabs(rawAngle - startingAngle) > bound) {
    waitingForStillness = true;
    motor.disable();
  }

  // ---- START RECOVERY ONLY AFTER VELOCITY IS VERY LOW ----
  if (waitingForStillness) {
    if (fabs(velFilt) < stillVelocityThreshold) {
      waitingForStillness = false;
      recoveryMode = true;
      recoveryJustStarted = true;

      // Hold the distance value at the moment recovery begins
      heldDistanceValue = distanceValue;

      motor.enable();
      resetPositionPID();
      positionTarget = startingAngle;
    }
  }

  // During recovery, keep output distance fixed
  if (recoveryMode) {
    distanceValue = heldDistanceValue;

    float velCmd = updatePositionPID(positionTarget, rawAngle);
    motor.move(velCmd);

    // Once recovery is complete, update offset so distance does NOT jump
    if (fabs(rawAngle - startingAngle) < returnTolerance) {
      motor.disable();
      recoveryMode = false;

      // Re-anchor the offset so the displayed/output distance remains continuous
      distanceOffset = (heldDistanceValue / LINEAR_MM_PER_RAD) - (rawAngle - startingAngle);
    }
  }

  command.run();

  // --- Diagnostics ---
  unsigned long now = millis();
  if (now - lastPrintMillis >= printInterval) {
    lastPrintMillis = now;

    // Serial.print("distanceValue: ");
    // Serial.print(distanceValue);
    // Serial.print("\t rotRelativeDeg: ");
    // Serial.print(rotRelativeDeg);
    // Serial.print("\t rotOutputDeg: ");
    // Serial.println(rotOutputDeg);

    Serial.print(distanceValue);
    Serial.print(",");
    Serial.println(rotRelativeDeg);
  }
}

float getFilteredVelocityFromAngle(float currentAngle) {
  unsigned long now = micros();

  if (!velInit) {
    velInit = true;
    prevAngle = currentAngle;
    prevMicros = now;
    filteredVelocity = 0.0f;
    return filteredVelocity;
  }

  float dt = (now - prevMicros) * 1e-6f;  // seconds
  if (dt <= 0.0f || dt > 0.5f) {
    // ignore crazy dt
    prevMicros = now;
    prevAngle = currentAngle;
    return filteredVelocity;
  }

  // raw velocity from angle
  float rawVel = (currentAngle - prevAngle) / dt;

  prevMicros = now;
  prevAngle = currentAngle;

  // Low-pass: alpha = dt / (tau + dt)
  float alpha = dt / (velTau + dt);
  filteredVelocity = filteredVelocity + alpha * (rawVel - filteredVelocity);

  return filteredVelocity;
}

float clampFloat(float x, float minVal, float maxVal) {
  if (x < minVal) return minVal;
  if (x > maxVal) return maxVal;
  return x;
}

float normalizeAngle(float angle) {
  // wrap to [0, 2pi)
  angle = fmodf(angle, TWO_PI);
  if (angle < 0.0f) {
    angle += TWO_PI;
  }
  // shift to (-pi, pi]
  if (angle > PI) {
    angle -= TWO_PI;
  }
  return angle;
}

float computePositionError(float target, float current) {
  float diff = target - current;
  return diff;
}

void initPositionPID(float Kp, float Ki, float Kd,
                     float outputLimit, float integralLimit) {
  positionPID.Kp = Kp;
  positionPID.Ki = Ki;
  positionPID.Kd = Kd;

  positionPID.integral = 0.0f;
  positionPID.previousError = 0.0f;
  positionPID.initialized = false;

  positionPID.outputLimit = (outputLimit > 0.0f) ? outputLimit : 0.0f;
  positionPID.integralLimit = (integralLimit > 0.0f) ? integralLimit : 0.0f;

  positionPID.lastMicros = micros();
}

void resetPositionPID() {
  positionPID.integral = 0.0f;
  positionPID.previousError = 0.0f;
  positionPID.initialized = false;
  positionPID.lastMicros = micros();
}

float updatePositionPID(float targetAngle, float currentAngle) {
  unsigned long now = micros();
  float dt = (now - positionPID.lastMicros) * 1e-6f;

  if (dt <= 0.0f || dt > 0.5f) {
    positionPID.lastMicros = now;
    return 0.0f;
  }

  positionPID.lastMicros = now;

  float error = computePositionError(targetAngle, currentAngle);

  if (!positionPID.initialized) {
    positionPID.previousError = error;
    positionPID.integral = 0.0f;
    positionPID.initialized = true;
  }

  positionPID.integral += error * dt;

  if (positionPID.integralLimit > 0.0f) {
    positionPID.integral = clampFloat(positionPID.integral,
                                      -positionPID.integralLimit,
                                      positionPID.integralLimit);
  }

  float derivative = (error - positionPID.previousError) / dt;
  positionPID.previousError = error;

  float output = positionPID.Kp * error
                 + positionPID.Ki * positionPID.integral
                 + positionPID.Kd * derivative;

  if (positionPID.outputLimit > 0.0f) {
    output = clampFloat(output, -positionPID.outputLimit, positionPID.outputLimit);
  }

  return output;
}

void setPositionTarget(float newTargetAngleRad) {
  positionTarget = newTargetAngleRad;
}

float readCurrentAngle() {
  return sensor1.getAngle();
}